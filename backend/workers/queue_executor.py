import asyncio
import time
import logging
import pandas as pd
from typing import Dict, Any, List
from backend.workers.job_registry import JobRegistry
from backend.workers.progress_tracker import ProgressTracker
from backend.workers.websocket_manager import ws_broadcaster
from backend.parallel.descriptor_pool import calculate_descriptors_multiprocess
from backend.cache.descriptor_cache import ScientificDescriptorCache
from backend.optimization.memory_guard import MemoryGuard
from backend.storage.memory_optimizer import downcast_dataframe, clean_memory

logger = logging.getLogger("sdo.backend.workers.queue")

# Shared queue and registries
task_queue: asyncio.Queue = asyncio.Queue()
active_tracker: Dict[str, ProgressTracker] = {}
job_registry = JobRegistry()
memory_guard = MemoryGuard()

async def process_enrichment_task(job_id: str, payload: Dict[str, Any]):
    """Processes a background computational toxicology enrichment task."""
    logger.info(f"Background worker starting enrichment job: {job_id}")
    
    # Update status to RUNNING
    job_registry.update_job(job_id, status="RUNNING", progress=0)
    
    df: pd.DataFrame = payload["df"]
    mappings: dict = payload["mappings"]
    selected_descriptors: List[str] = payload["selected_descriptors"]
    include_mordred: bool = payload["include_mordred"]
    mode: str = payload["mode"]
    
    # 1. Resolve column mappings to find SMILES & Name/CAS columns
    sci_to_user = {v: k for k, v in mappings.items()}
    smiles_col = sci_to_user.get('canonical_smiles') or sci_to_user.get('smiles')
    name_col = sci_to_user.get('chemical_name') or sci_to_user.get('chemical_id') or sci_to_user.get('cas_number')
    
    # If no smiles column is mapped, but we have a chemical name/CAS column, dynamically add canonical_smiles column
    if (not smiles_col or smiles_col not in df.columns) and name_col and name_col in df.columns:
        df['canonical_smiles'] = None
        mappings['canonical_smiles'] = 'canonical_smiles'
        sci_to_user['canonical_smiles'] = 'canonical_smiles'
        smiles_col = 'canonical_smiles'
        
    if not smiles_col or smiles_col not in df.columns:
        job_registry.update_job(job_id, status="FAILED", error="Ingested dataset lacks structural SMILES coordinate mapping or a mapped Chemical Name/CAS ID for auto-resolution.")
        await ws_broadcaster.broadcast({"job_id": job_id, "type": "JOB_FAILED", "error": "Lacks SMILES/Name mapping"})
        return

    # 2. Build Phase 1: Online & Cached Chemical Identity Resolution list
    unique_smiles_in_df = []
    if smiles_col in df.columns:
        unique_smiles_in_df = df[smiles_col].dropna().astype(str).str.strip().unique().tolist()
        unique_smiles_in_df = [s for s in unique_smiles_in_df if s]
        
    unique_names_to_resolve = []
    if name_col and name_col in df.columns:
        missing_smiles_mask = df[smiles_col].isna() | (df[smiles_col].astype(str).str.strip() == "")
        unique_names_to_resolve = df.loc[missing_smiles_mask, name_col].dropna().astype(str).str.strip().unique().tolist()
        unique_names_to_resolve = [n for n in unique_names_to_resolve if n]

    resolve_list = list(set(unique_smiles_in_df + unique_names_to_resolve))
    
    # Initialize phase 1 progress tracking
    tracker = ProgressTracker(job_id, len(resolve_list) if len(resolve_list) > 0 else 1)
    active_tracker[job_id] = tracker
    
    tracker.log(f"🧬 Starting Phase 1: Chemical Identity Resolution for {len(resolve_list)} unique inputs...")
    
    from backend.normalization.identifier_service import ChemicalIdentifierService
    id_service = ChemicalIdentifierService()
    
    resolved_mapping = {} # input_string -> canonical_smiles
    resolved_smiles_set = set()
    
    import os
    completed_resolutions = 0
    if resolve_list:
        for val in resolve_list:
            # Check for cancellation before processing each compound
            current_job = job_registry.get_job(job_id)
            if current_job and current_job.get("status") == "CANCELLED":
                tracker.log("🛑 Job execution aborted by cancellation instruction.")
                del active_tracker[job_id]
                clean_memory()
                return
                
            try:
                res = id_service.resolve(val)
                if res.get("canonical_smiles"):
                    cs = res["canonical_smiles"]
                    resolved_mapping[val] = cs
                    resolved_smiles_set.add(cs)
                else:
                    tracker.log(f"⚠️ Resolution failed for: '{val}' ({res.get('status') or 'not found'})")
            except Exception as e:
                tracker.log(f"⚠️ Exception during resolution of '{val}': {e}")
                
            completed_resolutions += 1
            if tracker.should_broadcast():
                tel = tracker.calculate_telemetry(completed_resolutions)
                tel["phase"] = "🔍 Phase 1: Identity Resolution"
                # Map progress to 0-35%
                mapped_progress = int((completed_resolutions / len(resolve_list)) * 35)
                _speed = tel.get("compounds_per_sec") or tel.get("items_per_sec", 0.0)
                _eta   = tel.get("eta_seconds", 0.0)
                job_registry.update_job(job_id, progress=mapped_progress, eta=_eta, speed=_speed)
                tel["progress_pct"] = mapped_progress
                await ws_broadcaster.broadcast({"job_id": job_id, "type": "PROGRESS", "data": tel})

    # Fill empty smiles values in the dataframe using the resolved mapping
    for idx, row in df.iterrows():
        sm_val = str(row[smiles_col]).strip() if pd.notna(row[smiles_col]) else ""
        if not sm_val and name_col and name_col in df.columns:
            name_val = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
            if name_val in resolved_mapping:
                df.at[idx, smiles_col] = resolved_mapping[name_val]
        elif sm_val in resolved_mapping:
            df.at[idx, smiles_col] = resolved_mapping[sm_val]

    # Filter resolved unique non-empty SMILES for offline descriptors phase
    unique_smiles = [s for s in resolved_smiles_set if s]
    total_compounds = len(unique_smiles)
    
    if total_compounds == 0:
        # Trivial success (no compounds resolved to calculate)
        os.makedirs("uploads/parquet", exist_ok=True)
        parquet_path = f"uploads/parquet/enriched_dataset_{job_id}.parquet"
        df.to_parquet(parquet_path, compression="SNAPPY", index=False)
        job_registry.update_job(job_id, status="COMPLETED", progress=100, result_path=parquet_path)
        await ws_broadcaster.broadcast({"job_id": job_id, "type": "JOB_COMPLETED"})
        del active_tracker[job_id]
        clean_memory()
        return

    # Update progress tracker to offline descriptors phase
    tracker = ProgressTracker(job_id, total_compounds)
    active_tracker[job_id] = tracker
    tracker.log(f"✓ Identity resolution phase complete. Resolved {total_compounds} unique canonical SMILES structures.")
    tracker.log(f"🧬 Initializing advanced offline descriptors calculations...")
    tracker.log(f"⚙️ Profile: '{mode.upper()}' | Extended Mordred: {include_mordred}")
    
    cache = ScientificDescriptorCache()
    cached_results = {}
    smiles_to_calculate = []
    
    # Check cache connection and database hit rates
    stats = cache.get_statistics()
    tracker.log(f"💾 SQLite Descriptor Cache status: {stats['total_cached_compounds']} molecules cached (Hit Rate: {stats['hit_rate_pct']}%)")

    # 3. Phase 2: Persistent SQLite Cache Lookup (Instant speedups)
    tracker.log("🔎 Starting Phase 2: Persistent SQLite Cache scan...")
    cache_hits = 0
    
    for smiles in unique_smiles:
        # Check cancellation state in cache lookup loop
        current_job = job_registry.get_job(job_id)
        if current_job and current_job.get("status") == "CANCELLED":
            tracker.log("🛑 Job execution aborted by cancellation instruction.")
            del active_tracker[job_id]
            clean_memory()
            return

        hit = cache.get(smiles, mode, include_mordred)
        if hit:
            cached_results[smiles] = {"success": True, "data": hit}
            cache_hits += 1
        else:
            smiles_to_calculate.append(smiles)

    tracker.log(f"✓ Cache scan completed: {cache_hits} hits (skipped calculations), {len(smiles_to_calculate)} misses scheduled for CPU calculations.")
    
    # Update client with initial cache outcomes (map progress to 35-50%)
    telemetry = tracker.calculate_telemetry(cache_hits)
    mapped_progress = 35 + int((cache_hits / total_compounds) * 15) if total_compounds > 0 else 50
    job_registry.update_job(job_id, progress=mapped_progress, eta=telemetry["eta_seconds"], speed=telemetry["compounds_per_sec"])
    telemetry["progress_pct"] = mapped_progress
    telemetry["phase"] = "⚗️ Phase 2: Cache Processing"
    await ws_broadcaster.broadcast({"job_id": job_id, "type": "PROGRESS", "data": telemetry})

    # 4. Phase 3: Isolated Multiprocess Calculations (ProcessPoolExecutor)
    calculation_results = {}
    if smiles_to_calculate:
        tracker.log(f"⚗️ Starting Phase 3: Spawning isolated CPU worker process pools...")
        
        # Get active running loop in main event thread to safe-schedule async broadcasts from executor threads
        loop = asyncio.get_running_loop()

        # Async progress wrapper to push counts over sockets
        def process_pool_callback(completed_count, total_count):
            cur_job = job_registry.get_job(job_id)
            if cur_job and cur_job.get("status") == "CANCELLED":
                raise Exception("JOB_CANCELLED")
                
            total_processed = cache_hits + completed_count
            tracker.log(f"Processed {total_processed}/{total_compounds} total compounds...")
            
            # Broadcast telemetry over websocket channel
            if tracker.should_broadcast():
                tel = tracker.calculate_telemetry(total_processed)
                # Map progress to 50-90%
                m_prog = 50 + int((completed_count / len(smiles_to_calculate)) * 40)
                _speed = tel.get("compounds_per_sec") or tel.get("items_per_sec", 0.0)
                _eta   = tel.get("eta_seconds", 0.0)
                job_registry.update_job(job_id, progress=m_prog, eta=_eta, speed=_speed)
                tel["progress_pct"] = m_prog
                tel["phase"] = "⚗️ Phase 3: Subprocess calculations"
                asyncio.run_coroutine_threadsafe(
                    ws_broadcaster.broadcast({"job_id": job_id, "type": "PROGRESS", "data": tel}),
                    loop
                )

        try:
            # Execute Process Pool in worker executor threads to avoid blocking asyncio loop
            calculation_results = await loop.run_in_executor(
                None, 
                calculate_descriptors_multiprocess,
                smiles_to_calculate,
                mode,
                include_mordred,
                process_pool_callback
            )
            
            # Write new calculation data back to sqlite cache
            tracker.log("💾 Writing calculated descriptors back to persistent SQLite cache database...")
            write_count = 0
            for sm, res in calculation_results.items():
                if res.get("success") and res.get("data"):
                    cache.put(sm, mode, include_mordred, res["data"])
                    write_count += 1
            tracker.log(f"✓ Cache synchronized: Added {write_count} records to SQLite cache database.")
            
        except Exception as exc:
            if "JOB_CANCELLED" in str(exc):
                tracker.log("🛑 Computation pipeline aborted by cancellation trigger.")
                job_registry.update_job(job_id, status="CANCELLED", error="Aborted by user.")
                await ws_broadcaster.broadcast({"job_id": job_id, "type": "JOB_CANCELLED"})
                del active_tracker[job_id]
                clean_memory()
                return
            else:
                logger.error(f"Error encountered in parallel processing worker: {exc}")
                job_registry.update_job(job_id, status="FAILED", error=str(exc))
                await ws_broadcaster.broadcast({"job_id": job_id, "type": "JOB_FAILED", "error": str(exc)})
                del active_tracker[job_id]
                clean_memory()
                return

    # 5. Phase 4: Data Assembly & Parquet Storage Writer (90-100% progress)
    tracker.log("📦 Starting Phase 4: Re-assembling enriched columns & writing binary Parquet dataset...")
    
    # Merge all cache + calculation dicts
    all_descriptor_results = {}
    all_descriptor_results.update(cached_results)
    all_descriptor_results.update(calculation_results)
    
    # Assemble complete enriched columns back into dataframe
    enriched_df = df.copy()
    
    # Find a sample descriptors dict to discover the returned column keys
    sample_desc = next((v["data"] for v in all_descriptor_results.values() if v.get("success") and v.get("data")), {})
    descriptor_keys = list(sample_desc.keys())
    
    # Add new descriptor columns
    for dk in descriptor_keys:
        if dk not in enriched_df.columns:
            enriched_df[dk] = None
            
    # Add PubChem_Error column if it doesn't exist
    if 'PubChem_Error' not in enriched_df.columns:
        enriched_df['PubChem_Error'] = None
            
    # Populate values row by row
    for idx, row in enriched_df.iterrows():
        sm = str(row[smiles_col]).strip() if pd.notna(row[smiles_col]) else ""
        if sm in all_descriptor_results:
            res = all_descriptor_results[sm]
            if res.get("success") and res.get("data"):
                for dk, val in res["data"].items():
                    enriched_df.at[idx, dk] = val
            elif res.get("error"):
                enriched_df.at[idx, 'PubChem_Error'] = res["error"]
        else:
            enriched_df.at[idx, 'PubChem_Error'] = "SMILES_NOT_RESOLVED"

    # Cast new descriptor columns to true numerical values where possible
    for dk in descriptor_keys:
        try:
            enriched_df[dk] = pd.to_numeric(enriched_df[dk], errors='coerce')
        except Exception:
            pass

    # Automatic floating/integer compression optimization
    tracker.log("⚡ Compacting RAM sizing: Downcasting float64/int64 columns to float32/int32...")
    compressed_df = downcast_dataframe(enriched_df)
    
    # Save optimized Parquet file
    os.makedirs("uploads/parquet", exist_ok=True)
    parquet_path = f"uploads/parquet/enriched_dataset_{job_id}.parquet"
    try:
        compressed_df.to_parquet(parquet_path, compression="SNAPPY", index=False)
        tracker.log(f"✓ Binary snappied Parquet storage engine online: Saved successfully to {parquet_path}.")
    except Exception as pq_err:
        logger.warning(f"Parquet engine writing failed, falling back to compressed Feather: {pq_err}")
        parquet_path = f"uploads/parquet/enriched_dataset_{job_id}.feather"
        compressed_df.to_feather(parquet_path)

    # 6. Mark Job completed successfully
    tracker.log("🏁 Scientific workflow complete! Releasing RAM locks.")
    job_registry.update_job(job_id, status="COMPLETED", progress=100, result_path=parquet_path)
    
    # Telemetry broadcast
    final_tel = tracker.calculate_telemetry(total_compounds)
    final_tel["progress_pct"] = 100
    final_tel["phase"] = "🏁 Complete"
    await ws_broadcaster.broadcast({"job_id": job_id, "type": "JOB_COMPLETED", "data": final_tel})
    
    # Memory Guard Cleanup
    del active_tracker[job_id]
    clean_memory()

async def process_segregation_task(job_id: str, payload: Dict[str, Any]):
    """
    5-Phase scientific hierarchy construction with real-time progress.

    Phase 1 (0-10%):  Dedup + canonicalization (preserved)
    Phase 2 (10-25%): Initialise LineageBuilder, log hierarchy plan
    Phase 3 (25-85%): Recursive node construction via run_in_executor
    Phase 4 (85-95%): Node DataFrames + export files already saved
    Phase 5 (95-100%): Finalise, broadcast JOB_COMPLETED with lineage
    """
    import psutil
    logger.info(f"Background worker starting segregation job: {job_id}")
    job_registry.update_job(job_id, status="RUNNING", progress=0)

    df: pd.DataFrame = payload["df"]
    hierarchy: List[str] = payload["hierarchy"]
    context_id: str = payload["context_id"]

    tracker = ProgressTracker(job_id, 100)
    active_tracker[job_id] = tracker

    try:
        # ── Phase 1: Dedup + canonicalization (0-15%) ────────────────────────
        tracker.log("🌲 Phase 1: Dedup & canonicalization…")
        job_registry.update_job(job_id, progress=5)
        await ws_broadcaster.broadcast({
            "job_id": job_id, "type": "PROGRESS",
            "data": {"progress_pct": 5, "phase": "🌲 Phase 1: Dedup & canonicalization"},
        })

        # --- Biological Variance & Deduplication (Streamlit Parity) ---
        enable_dedup = payload.get("enable_dedup", False)
        prune_high_variance = payload.get("prune_high_variance", False)

        from backend.core.workspace_registry import registry as _reg
        _ctx = _reg.get_context(context_id)
        if _ctx and _ctx.mappings:
            if enable_dedup:
                from backend.validation.duplicate_detector import SmartDeduplicator
                dedup = SmartDeduplicator()
                df, dedup_res = dedup.deduplicate(df, _ctx.mappings)
                if dedup_res.duplicates_removed > 0:
                    tracker.log(f"✂️ Deduplication removed {dedup_res.duplicates_removed} exact duplicates across {len(dedup_res.keys_used)} mapped columns.")
            
            if prune_high_variance or payload.get("enable_variance_pruning", False):
                from backend.processing.auditor import ScientificAuditor
                auditor = ScientificAuditor()
                # Run the fully-vectorized log10 variance audit
                flagged_df, vs = auditor.compute_variance_flags(df, _ctx.mappings)
                if vs:
                    if prune_high_variance:
                        pre_len = len(df)
                        df = flagged_df[flagged_df['audit_flag'] != 'High_Variance_Conflict'].copy()
                        dropped = pre_len - len(df)
                        if dropped > 0:
                            tracker.log(f"✂️ Variance Pruning dropped {dropped} records (High_Variance_Conflict). Consistency: {vs.consistency_score}%")
                    else:
                        tracker.log(f"ℹ️ Variance Audit complete. Consistency score: {vs.consistency_score}% ({vs.conflict_count} conflicts identified).")
                else:
                    tracker.log("⚠️ Variance logic skipped: could not resolve chemical, endpoint, or value mappings.")

        await asyncio.sleep(0.01)  # Yield to event loop

        # ── Phase 2: Initialise LineageBuilder (15-25%) ──────────────────────
        from backend.core.workspace_registry import registry
        context = registry.get_context(context_id)
        mappings = context.mappings or {}

        tracker.log(
            f"🌿 Phase 2: Initialising LineageBuilder — "
            f"{len(df)} rows × {len(hierarchy)} hierarchy levels: {hierarchy}"
        )
        job_registry.update_job(job_id, progress=15)
        await ws_broadcaster.broadcast({
            "job_id": job_id, "type": "PROGRESS",
            "data": {
                "progress_pct": 15,
                "phase": "🌿 Phase 2: Initialising hierarchy engine",
                "active_node": "Root",
                "rows_remaining": len(df),
                "memory_usage": f"{psutil.virtual_memory().percent:.1f}%",
            },
        })

        # ── Phase 3: CPU-heavy recursive tree construction (25-85%) ──────────
        tracker.log("⚙️ Phase 3: Launching thread-pool for recursive tree build…")
        job_registry.update_job(job_id, progress=25)
        
        # Estimate total work: root node (len(df)) + each level sum (len(df))
        total_work = len(df) * (len(hierarchy) + 1)
        tree_tracker = ProgressTracker(job_id, total_work)
        active_tracker[job_id] = tree_tracker

        loop = asyncio.get_running_loop()
        
        # Shared state for the sync callback
        processed_state = {"rows": 0}
        
        def sync_broadcast(event: dict):
            # Track work based on the size of the node processed
            processed_state["rows"] += event.get("rows_remaining", 0)
            tree_tracker.items_processed = processed_state["rows"]
            
            tel = tree_tracker.calculate_telemetry(processed_state["rows"])
            
            # Map 0-100 progress of tree build to 25-85% of total job
            mapped_prog = 25 + (tel["progress_pct"] * 0.60)
            
            # Throttle database writes to avoid locking SQLite
            if processed_state["rows"] % max(1, (total_work // 20)) == 0:
                speed = tel.get("compounds_per_sec") or tel.get("items_per_sec", 0.0)
                eta   = tel.get("eta_seconds", 0.0)
                job_registry.update_job(job_id, progress=int(mapped_prog), eta=eta, speed=speed)
            
            speed = tel.get("compounds_per_sec") or tel.get("items_per_sec", 0.0)
            eta   = tel.get("eta_seconds", 0.0)
            asyncio.run_coroutine_threadsafe(
                ws_broadcaster.broadcast({
                    "job_id": job_id, "type": "PROGRESS",
                    "data": {
                        "progress_pct": int(mapped_prog),
                        "phase": event.get("phase", "🌿 Phase 3: Building hierarchy tree…"),
                        "active_node": event.get("active_node", "Root"),
                        "rows_remaining": event.get("rows_remaining", len(df)),
                        "memory_usage": f"{psutil.virtual_memory().percent:.1f}%",
                        "eta_seconds": eta,
                        "compounds_per_sec": speed,
                        "items_per_sec": speed,
                    },
                }),
                loop
            )

        from backend.core.lineage_builder import LineageBuilder

        lineage_data: dict = await loop.run_in_executor(
            None,
            lambda: LineageBuilder.run(
                df=df,
                hierarchy_cols=hierarchy,
                mappings=mappings,
                workspace_id=context_id,
                broadcast_fn=sync_broadcast,
            ),
        )

        tracker.log(
            f"✓ Hierarchy tree complete: {lineage_data['total_nodes']} nodes, "
            f"max depth {lineage_data['max_depth']}."
        )

        # ── Phase 4: Exports already saved by LineageBuilder (85-95%) ────────
        job_registry.update_job(job_id, progress=90)
        await ws_broadcaster.broadcast({
            "job_id": job_id, "type": "PROGRESS",
            "data": {
                "progress_pct": 90,
                "phase": "📦 Phase 4: Exports persisted — finalising context…",
                "memory_usage": f"{psutil.virtual_memory().percent:.1f}%",
            },
        })
        await asyncio.sleep(0.01)

        # ── Phase 5: Store engine + broadcast JOB_COMPLETED (95-100%) ────────
        # Extract the live engine object (attached by LineageBuilder.run)
        engine = lineage_data.pop("_engine", None)

        context.active_lineage = lineage_data
        context.active_segregation_result = lineage_data  # backward-compat alias
        context.hierarchy_engine = engine
        context.add_trace("segregate")

        job_registry.update_job(job_id, status="COMPLETED", progress=100, result_path="Lineage Engine")
        tracker.log("🏁 Phase 5: Hierarchy engine online. Broadcasting JOB_COMPLETED.")

        await ws_broadcaster.broadcast({
            "job_id": job_id,
            "type": "JOB_COMPLETED",
            "data": {
                "lineage": lineage_data,
            },
        })

    except Exception as e:
        logger.error(f"Segregation job {job_id} failed: {e}", exc_info=True)
        job_registry.update_job(job_id, status="FAILED", error=str(e))
        await ws_broadcaster.broadcast({
            "job_id": job_id,
            "type": "JOB_FAILED",
            "error": str(e),
        })

    finally:
        if job_id in active_tracker:
            del active_tracker[job_id]
        clean_memory()


async def queue_worker_loop():
    """Infinite background asynchronous task runner managing execution queues and safety guards."""
    logger.info("Initializing infinite background task queue worker loop...")
    while True:
        try:
            # 1. Fetch next queued job
            job_id, payload = await task_queue.get()
            
            # 2. Check Memory Safety Shield (Emergency Throttle Guard!)
            is_safe, reason = memory_guard.verify_safety_shield()
            if not is_safe:
                # Memory critical (RAM > 85%) - pause queue execution
                logger.critical(f"Task Queue Executor paused. Reason: {reason}. Sweeping RAM and waiting for stabilization...")
                memory_guard.emergency_garbage_sweep()
                
                # Check memory availability every 5 seconds before resuming
                while not is_safe:
                    await asyncio.sleep(5.0)
                    is_safe, reason = memory_guard.verify_safety_shield()
                    
                logger.info("Memory usage stabilized. Resuming background queue task executions.")
            
            # 3. Process task
            task_type = payload.get("type", "enrichment")
            if task_type == "enrichment":
                await process_enrichment_task(job_id, payload)
            elif task_type == "segregation":
                await process_segregation_task(job_id, payload)
            else:
                logger.error(f"Unknown task type: {task_type}")
            
            # Mark queued task completed
            task_queue.task_done()
            
        except asyncio.CancelledError:
            logger.info("Background task queue worker loop received cancel signal.")
            break
        except Exception as e:
            logger.error(f"Critical exception in background task queue worker loop: {e}")
            await asyncio.sleep(2.0) # Graceful delay before re-looping

def start_background_worker_queue():
    """Starts the queue execution loop in the asyncio background."""
    asyncio.create_task(queue_worker_loop())
    asyncio.create_task(ws_broadcaster.start_heartbeat_monitor())

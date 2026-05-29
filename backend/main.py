import os
import json
import time
import logging
import asyncio
import zipfile
import io
from typing import Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import multiprocessing

# Windows Multiprocessing Fix (Improvement 8)
if __name__ == '__main__':
    multiprocessing.freeze_support()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("sdo.backend.gateway")

from backend.core.workspace_registry import registry, registry_cleanup_loop
from backend.core.pipeline_controller import ScientificPipelineController
from backend.workers.queue_executor import start_background_worker_queue, job_registry
from backend.workers.websocket_manager import ws_broadcaster
from backend.workers.task_manager import TaskManager
from backend.optimization.memory_guard import MemoryGuard
from backend.api.validators.request_validator import (
    BaseClientPayload, CurationPayload, MappingPayload,
    SchemaInferPayload, SegregatePayload, EnrichmentPayload,
    validate_uploaded_file
)
from backend.api.routes.hierarchy_routes import router as hierarchy_router
from backend.api.routes.descriptor_routes import router as descriptor_router
from backend.api.routes.modeling_routes import router as modeling_router
from backend.core.config import settings

app = FastAPI(title="Scientific Data Orchestrator", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular API routers
app.include_router(hierarchy_router)
app.include_router(descriptor_router)
app.include_router(modeling_router)

memory_guard = MemoryGuard()

# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health")
async def api_health():
    """Lightweight health probe for load balancers, Playwright, and monitoring."""
    import psutil
    return {
        "status": "ok",
        "version": "4.0",
        "engine": "SUTRIX",
        "ram_pct": psutil.virtual_memory().percent,
        "cpu_pct": psutil.cpu_percent(interval=None),
    }


@app.on_event("startup")
async def startup_event():
    logger.info("SUTRIX Pipeline Engine launching...")
    from backend.logging.logger import initialize_sentry
    from backend.database.session import init_db
    
    initialize_sentry()
    
    # Ensure database schema is initialized
    init_db()

    # Inject WS broadcaster into pipeline manager
    from backend.core.pipeline_task_manager import pipeline_manager
    pipeline_manager.inject_broadcaster(ws_broadcaster)

    start_background_worker_queue()
    asyncio.create_task(registry_cleanup_loop())
    asyncio.create_task(ws_broadcaster.start_heartbeat_monitor())

# ── 1. FILE INGESTION (ASYNC — returns job_id immediately) ────────────────────────────────────────
async def _run_ingest_background(job_id: str, client_id: str, filename: str, temp_path: str, file_bytes: bytes):
    """Background coroutine: parse file and stream progress via WebSocket."""
    from backend.core.pipeline_task_manager import pipeline_manager
    from backend.core.pipeline_stages import PipelineStage
    from backend.workers.progress_tracker import ProgressTracker

    job = pipeline_manager.get_job(job_id)
    if not job:
        return

    job.status = "RUNNING"
    job.started_at = time.time() if hasattr(job, 'started_at') else None

    try:
        # Stage: PARSING
        await pipeline_manager.broadcast_stage_change(job, PipelineStage.PARSING, f"Reading {filename}...")
        context = registry.get_context(client_id)
        result = await ScientificPipelineController.ingest_dataset(context, filename, temp_path, file_bytes)

        # Stage: SCHEMA_DETECTION
        await pipeline_manager.broadcast_stage_change(job, PipelineStage.SCHEMA_DETECTION, "Identifying scientific variable columns...")
        await asyncio.sleep(0.1)  # allow WS flush

        # Stage: WORKSPACE_READY
        await pipeline_manager.broadcast_stage_change(job, PipelineStage.WORKSPACE_READY, "Dataset fully preprocessed.")
        await pipeline_manager.broadcast_completed(job, result)

    except Exception as e:
        logger.error(f"Background ingest failed: {e}")
        await pipeline_manager.broadcast_failed(job, str(e))


@app.post("/api/ingest")
async def api_ingest(file: UploadFile = File(...), client_id: str = Form(...)):
    is_safe, msg = memory_guard.verify_safety_shield()
    if "EMERGENCY" in msg:
        raise HTTPException(status_code=503, detail=msg)

    from backend.core.pipeline_task_manager import pipeline_manager
    from backend.core.pipeline_stages import PipelineStage

    try:
        file_bytes = await file.read()
        validate_uploaded_file(file.filename, len(file_bytes), file.content_type)
        active_uploads = os.path.join(settings.UPLOAD_DIR, "active")
        os.makedirs(active_uploads, exist_ok=True)
        temp_path = os.path.join(active_uploads, file.filename)
        with open(temp_path, "wb") as f:
            f.write(file_bytes)

        # Create job and return IMMEDIATELY
        job = pipeline_manager.create_job(client_id, "upload", total_items=1)
        file_size_mb = round(len(file_bytes) / (1024 * 1024), 2)
        eta = pipeline_manager.estimate_upload_eta(file_size_mb, len(file_bytes) // 100)

        # Fire background task
        asyncio.create_task(_run_ingest_background(job.job_id, client_id, file.filename, temp_path, file_bytes))

        return {
            "job_id":      job.job_id,
            "status":      "PROCESSING",
            "filename":    file.filename,
            "file_size_mb": file_size_mb,
            "eta_seconds": eta,
        }
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_demo_ingest_background(job_id: str, client_id: str, demo_path: str, file_bytes: bytes):
    """Background coroutine for demo dataset ingestion."""
    from backend.core.pipeline_task_manager import pipeline_manager
    from backend.core.pipeline_stages import PipelineStage

    job = pipeline_manager.get_job(job_id)
    if not job:
        return

    job.status = "RUNNING"
    try:
        await pipeline_manager.broadcast_stage_change(job, PipelineStage.PARSING, "Loading eco-toxicity demo dataset...")
        context = registry.get_context(client_id)
        result = await ScientificPipelineController.ingest_dataset(context, "eco_toxicity_dataset.csv", demo_path, file_bytes)

        await pipeline_manager.broadcast_stage_change(job, PipelineStage.SCHEMA_DETECTION, "Detecting toxicological schema...")
        await asyncio.sleep(0.05)
        await pipeline_manager.broadcast_stage_change(job, PipelineStage.WORKSPACE_READY, "Demo workspace ready.")
        await pipeline_manager.broadcast_completed(job, result)
    except Exception as e:
        logger.error(f"Demo background ingest failed: {e}")
        await pipeline_manager.broadcast_failed(job, str(e))


@app.post("/api/demo_ingest")
async def api_demo_ingest(client_id: str = Form(...)):
    is_safe, msg = memory_guard.verify_safety_shield()
    if "EMERGENCY" in msg:
        raise HTTPException(status_code=503, detail=msg)

    from backend.core.pipeline_task_manager import pipeline_manager
    from backend.core.pipeline_stages import PipelineStage

    try:
        # Search for demo file: check data/ first, then project root, then backend root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(project_root, "data", "eco_toxicity_dataset.csv"),
            os.path.join(project_root, "eco_toxicity_dataset.csv"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "eco_toxicity_dataset.csv"),
        ]
        demo_path = next((p for p in candidates if os.path.exists(p)), None)
        if not demo_path:
            raise FileNotFoundError(f"eco_toxicity_dataset.csv not found. Searched: {candidates}")

        with open(demo_path, "rb") as f:
            file_bytes = f.read()

        file_size_mb = round(len(file_bytes) / (1024 * 1024), 2)
        job = pipeline_manager.create_job(client_id, "upload", total_items=1)
        eta = pipeline_manager.estimate_upload_eta(file_size_mb, len(file_bytes) // 100)

        asyncio.create_task(_run_demo_ingest_background(job.job_id, client_id, demo_path, file_bytes))

        return {
            "job_id":       job.job_id,
            "status":       "PROCESSING",
            "filename":     "eco_toxicity_dataset.csv",
            "file_size_mb": file_size_mb,
            "eta_seconds":  eta,
        }
    except Exception as e:
        logger.error(f"Demo Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 2. MAPPING & CURATION ────────────────────────────────────────
@app.post("/api/curate")
async def api_curate(payload: CurationPayload):
    try:
        context = registry.get_context(payload.client_id)
        return await ScientificPipelineController.curate_columns(context, payload.columns_to_drop)
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mapping")
async def api_mapping(payload: MappingPayload):
    try:
        context = registry.get_context(payload.client_id)
        return await ScientificPipelineController.apply_column_mapping(context, payload.mappings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from backend.core.schema_intelligence import SchemaIntelligenceEngine

@app.post("/api/schema/infer")
async def api_schema_infer(payload: SchemaInferPayload):
    try:
        inferred = SchemaIntelligenceEngine.infer_schema(payload.columns)
        return {"mappings": inferred}
    except Exception as e:
        logger.error(f"Schema Inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 3. SEGREGATION ────────────────────────────────────────
@app.post("/api/segregate")
async def api_segregate(payload: SegregatePayload):
    try:
        context = registry.get_context(payload.client_id)
        job_id = await ScientificPipelineController.perform_segmentation(
            context=context,
            enable_dedup=payload.enable_dedup,
            enable_variance_pruning=payload.enable_variance_pruning,
            prune_high_variance=payload.prune_high_variance,
            selected_hierarchy=payload.selected_hierarchy
        )
        return {"job_id": job_id, "status": "QUEUED"}
    except Exception as e:
        logger.error(f"Segregation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 4. ENRICHMENT ────────────────────────────────────────
@app.post("/api/jobs/enrich")
async def api_enrich_submit(payload: EnrichmentPayload):
    try:
        context = registry.get_context(payload.client_id)
        job_id = await ScientificPipelineController.run_enrichment(
            context, payload.selected_descriptors, payload.include_mordred, payload.mode
        )
        return {"job_id": job_id, "status": "QUEUED"}
    except Exception as e:
        logger.error(f"Enrichment job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{client_id}/status")
async def api_job_status(client_id: str):
    context = registry.get_context(client_id)
    if not context.active_job_id:
        raise HTTPException(status_code=404, detail="No active job")
    status = TaskManager.query_status(context.active_job_id)
    return status

@app.post("/api/jobs/{client_id}/cancel")
async def api_job_cancel(client_id: str):
    context = registry.get_context(client_id)
    if not context.active_job_id:
        raise HTTPException(status_code=404, detail="No active job")
    success = TaskManager.cancel_job(context.active_job_id)
    return {"success": success}

@app.get("/api/jobs/{client_id}/result")
async def api_job_result(client_id: str, job_id: str = None):
    try:
        context = registry.get_context(client_id)
        # If an explicit job_id is provided by the frontend, always use it.
        # This bypasses any stale context.active_job_id from a previous phase (e.g. segregation).
        effective_job_id = job_id or context.active_job_id
        if not effective_job_id:
            raise HTTPException(status_code=400, detail="No job_id provided and no active job in workspace.")
        # Temporarily override context for this call so assemble_enrichment_result uses the right job
        original_job_id = context.active_job_id
        context.active_job_id = effective_job_id
        try:
            result = await ScientificPipelineController.assemble_enrichment_result(context)
        finally:
            # Restore original so we don't permanently mutate context with a query param
            context.active_job_id = effective_job_id  # keep the enrichment job as active
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── 5. READINESS ────────────────────────────────────────
@app.post("/api/readiness")
async def api_readiness(payload: BaseClientPayload):
    try:
        context = registry.get_context(payload.client_id)
        return await ScientificPipelineController.run_readiness_analysis(context)
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 6. TELEMETRY ─────────────────────────────────────
@app.get("/api/telemetry")
async def api_telemetry():
    status = memory_guard.get_memory_status()
    from backend.cache.descriptor_cache import ScientificDescriptorCache
    cache = ScientificDescriptorCache()
    cache_stats = cache.get_statistics()
    status["cache_hit_rate_pct"] = cache_stats["hit_rate_pct"]
    status["total_cached_compounds"] = cache_stats["total_cached_compounds"]
    status["active_jobs_count"] = len(job_registry.get_active_jobs())
    status["active_workspaces"] = len(registry.workspaces)
    return status

# ── 6b. COMPLIANCE & SEGREGATION DOWNLOADS ─────────────────
@app.get("/api/segregate/{client_id}/download")
async def api_segregate_download(client_id: str):
    try:
        context = registry.get_context(client_id)
        result = context.active_segregation_result
        if not result:
            raise HTTPException(status_code=404, detail="No segregation result found in session context.")
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for leaf in result.leaf_nodes:
                rel_path = leaf['path']
                filename = leaf['filename']
                file_buffer = leaf.get('buffer')
                if file_buffer:
                    zip_entry_path = f"{result.root_path}/{rel_path}/{filename}" if rel_path else f"{result.root_path}/{filename}"
                    zipf.writestr(zip_entry_path, file_buffer.getvalue())
                    
        from fastapi import Response
        filename = f"SDO_Raw_Segregation_{client_id}.zip"
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Segregation download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/{client_id}/report")
async def api_compliance_report(client_id: str):
    try:
        context = registry.get_context(client_id)
        df = context.load_slice()
        
        # 1. Run audit
        from backend.processing.auditor import ScientificAuditor
        auditor = ScientificAuditor()
        report = auditor.audit(df, context.mappings, dataset_id=client_id)
        
        # 2. Recover stats
        seg_stats = context.segmentation_results or {}
        variance_summary = None
        if context.active_segregation_result:
            if isinstance(context.active_segregation_result, dict):
                variance_summary = context.active_segregation_result.get("variance_summary")
            else:
                variance_summary = getattr(context.active_segregation_result, "variance_summary", None)
            
        dedup_stats_dict = None
        if "dedup_stats" in seg_stats and seg_stats["dedup_stats"]:
            d = seg_stats["dedup_stats"]
            dedup_stats_dict = {
                "original_count": d["original_count"],
                "deduplicated_count": d["deduplicated_count"],
                "duplicates_removed": d["duplicates_removed"],
                "duplicate_groups": d["duplicate_groups"],
            }
            
        from backend.exports.pdf_generator import AuditPDFGenerator
        pdf_gen = AuditPDFGenerator()
        pdf_io = pdf_gen.generate_report(
            audit_report=report,
            dataset_name=f"dataset_{client_id}",
            session_id=client_id,
            variance_report=variance_summary,
            dedup_stats=dedup_stats_dict,
        )
        
        from fastapi import Response
        filename = f"Scientific_Audit_Report_{client_id}.pdf"
        return Response(
            content=pdf_io.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Compliance report download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/{client_id}/download")
async def api_compliance_download(client_id: str):
    try:
        context = registry.get_context(client_id)
        if not context.active_lineage:
            raise HTTPException(status_code=404, detail="No lineage found in session context. Map columns and run segregation first.")
            
        df = context.load_slice()
        
        # 1. Run audit
        from backend.processing.auditor import ScientificAuditor
        auditor = ScientificAuditor()
        report = auditor.audit(df, context.mappings, dataset_id=client_id)
        
        # 2. Recover stats
        seg_stats = context.segmentation_results or {}
        variance_summary = None
        if context.active_segregation_result:
            if isinstance(context.active_segregation_result, dict):
                variance_summary = context.active_segregation_result.get("variance_summary")
            else:
                variance_summary = getattr(context.active_segregation_result, "variance_summary", None)

        dedup_stats_dict = None
        if "dedup_stats" in seg_stats and seg_stats["dedup_stats"]:
            d = seg_stats["dedup_stats"]
            dedup_stats_dict = {
                "original_count": d["original_count"],
                "deduplicated_count": d["deduplicated_count"],
                "duplicates_removed": d["duplicates_removed"],
                "duplicate_groups": d["duplicate_groups"],
            }
        
        from backend.exports.pdf_generator import AuditPDFGenerator
        pdf_gen = AuditPDFGenerator()
        pdf_io = pdf_gen.generate_report(
            audit_report=report,
            dataset_name=f"dataset_{client_id}",
            session_id=client_id,
            variance_report=variance_summary,
            dedup_stats=dedup_stats_dict,
        )
        
        # 3. Assemble compliance ZIP using new HierarchyEngine
        import zipfile
        import json
        import pandas as pd
        import xlsxwriter
        import re
        import urllib.parse
        import io
        import os

        engine = context.hierarchy_engine
        lineage = context.active_lineage
        
        zip_buffer = io.BytesIO()
        
        REL_MAP = { ">=": "GTE", "<=": "LTE", "=": "EQ", ">": "GT", "<": "LT" }
        def sanitize_folder_name(name: str) -> str:
            for op, safe_str in REL_MAP.items():
                name = name.replace(op, safe_str)
            name = re.sub(r'[<>:"/\\|?*]', '_', name)
            return name.strip()

        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Scientific_Audit_Report.pdf", pdf_io.getvalue())
            
            manifest = {
                "client_id": client_id,
                "total_nodes": lineage.get("total_nodes", 0),
                "max_depth": lineage.get("max_depth", 0),
                "root_id": lineage.get("root_id", "root"),
                "nodes": [
                    {
                        "id": n.get("id"),
                        "path": n.get("path", ""),
                        "filter_col": n.get("filter_col", ""),
                        "filter_val": n.get("filter_val", ""),
                        "row_count": n.get("row_count", 0),
                        "is_leaf": n.get("is_leaf", False),
                        "level": n.get("level", 0),
                    }
                    for n in lineage.get("nodes", [])
                ],
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

            nodes_added = 0
            leaf_records = []

            for node_id, detail in engine.node_details.items():
                metadata = detail.get("metadata", {}) if isinstance(detail.get("metadata"), dict) else {}
                node_path = metadata.get("path", node_id)
                is_leaf = metadata.get("is_leaf", False)

                folder_parts = [sanitize_folder_name(p) for p in str(node_path).split(" > ")]
                folder_path = "/".join(folder_parts) + "/"

                export_dir = detail.get("_export_dir")
                node_df = None

                if is_leaf and export_dir:
                    if os.path.isfile(os.path.join(export_dir, "dataset.parquet")):
                        try:
                            node_df = pd.read_parquet(os.path.join(export_dir, "dataset.parquet"))
                        except Exception: pass
                    if node_df is None and os.path.isfile(os.path.join(export_dir, "dataset.csv")):
                        try:
                            node_df = pd.read_csv(os.path.join(export_dir, "dataset.csv"))
                        except Exception: pass

                if node_df is not None:
                    # Export directly to XLSX for final user
                    excel_data = io.BytesIO()
                    node_df.to_excel(excel_data, index=False, engine="openpyxl")
                    zf.writestr(folder_path + "data.xlsx", excel_data.getvalue())
                    
                    if export_dir and os.path.isfile(os.path.join(export_dir, "dataset.parquet")):
                        with open(os.path.join(export_dir, "dataset.parquet"), "rb") as pf:
                            zf.writestr(folder_path + "data.parquet", pf.read())

                    nodes_added += 1
                    
                    leaf_records.append({
                        "filename": "data.xlsx",
                        "rel_path": folder_path.rstrip("/"),
                        "records": len(node_df),
                        "compounds": metadata.get("unique_compounds", 0)
                    })

            if leaf_records:
                excel_buf = io.BytesIO()
                workbook = xlsxwriter.Workbook(excel_buf, {'in_memory': True})
                worksheet = workbook.add_worksheet("Master Index")
                header_format = workbook.add_format({'bold': True, 'bg_color': '#002147', 'font_color': 'white', 'border': 1})
                link_format = workbook.add_format({'font_color': 'blue', 'underline': 1})
                
                headers = ["File Name", "Relative Path", "Records", "Compounds", "Link"]
                for col_num, header in enumerate(headers):
                    worksheet.write(0, col_num, header, header_format)
                worksheet.set_column('A:A', 20)
                worksheet.set_column('B:B', 50)
                
                for row_num, leaf in enumerate(leaf_records, start=1):
                    worksheet.write_string(row_num, 0, leaf["filename"])
                    worksheet.write_string(row_num, 1, leaf["rel_path"])
                    worksheet.write_number(row_num, 2, leaf["records"])
                    worksheet.write_number(row_num, 3, leaf["compounds"])
                    full_rel_path = f'{leaf["rel_path"]}/{leaf["filename"]}'
                    encoded_path = urllib.parse.quote(full_rel_path, safe='/')
                    worksheet.write_url(row_num, 4, f"external:{encoded_path}", link_format, string="Open File")
                    
                workbook.close()
                zf.writestr("Master_Index.xlsx", excel_buf.getvalue())
                
        from fastapi import Response
        filename = f"SDO_Compliance_{client_id}.zip"
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Compliance package download failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ── 7. WEBSOCKET ──────────────────────────────────────
@app.websocket("/ws/jobs/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Observation ONLY. No mutations permitted."""
    await ws_broadcaster.connect(client_id, websocket)
    
    # Send immediate state recovery frame to prevent WebSocket race conditions (stale/fast jobs)
    try:
        context = registry.get_context(client_id)
        if context and context.active_job_id:
            job = job_registry.get_job(context.active_job_id)
            if job:
                status = job.get("status")
                if status == "COMPLETED":
                    await websocket.send_text(json.dumps({
                        "job_id": context.active_job_id,
                        "type": "JOB_COMPLETED",
                        "data": {
                            "progress_pct": 100,
                            "eta_seconds": 0.0,
                            "compounds_per_sec": job.get("compounds_per_sec", 0.0),
                            "phase": "Complete",
                            "logs": ["🏁 Scientific workflow complete! Releasing RAM locks."]
                        }
                    }))
                elif status == "FAILED":
                    await websocket.send_text(json.dumps({
                        "job_id": context.active_job_id,
                        "type": "JOB_FAILED",
                        "error": job.get("error_message") or "Unknown error"
                    }))
                elif status == "CANCELLED":
                    await websocket.send_text(json.dumps({
                        "job_id": context.active_job_id,
                        "type": "JOB_CANCELLED"
                    }))
                elif status in ["RUNNING", "QUEUED"]:
                    await websocket.send_text(json.dumps({
                        "job_id": context.active_job_id,
                        "type": "PROGRESS",
                        "data": {
                            "progress_pct": job.get("progress", 0),
                            "eta_seconds": job.get("eta_seconds", 0.0),
                            "compounds_per_sec": job.get("compounds_per_sec", 0.0),
                            "phase": "🔍 Running" if status == "RUNNING" else "⏳ Queued",
                            "logs": ["Active task context re-established."]
                        }
                    }))
    except Exception as e:
        logger.error(f"Failed to send state recovery frame: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "PONG":
                pass
    except WebSocketDisconnect:
        ws_broadcaster.disconnect(client_id)
    except Exception as e:
        ws_broadcaster.disconnect(client_id)


# ── JOB CANCEL ─────────────────────────────────────────
@app.post("/api/jobs/{job_id}/cancel")
async def api_cancel_job(job_id: str):
    from backend.core.pipeline_task_manager import pipeline_manager
    cancelled = pipeline_manager.cancel_job(job_id)
    if cancelled:
        job = pipeline_manager.get_job(job_id)
        if job:
            await pipeline_manager.broadcast_partial_save(job)
        return {"status": "CANCELLED", "job_id": job_id}
    raise HTTPException(status_code=404, detail="Job not found or not running")


@app.get("/api/jobs/{job_id}/state")
async def api_job_state(job_id: str):
    from backend.core.pipeline_task_manager import pipeline_manager
    job = pipeline_manager.get_job(job_id)
    if job:
        return job.to_dict()
    raise HTTPException(status_code=404, detail="Job not found")


@app.get("/api/jobs/{job_id}")
async def api_job_poll(job_id: str):
    """Polling endpoint for frontend fallback when WebSocket misses JOB_COMPLETED.
    Returns status + result so the UI can hydrate without WebSocket delivery."""
    from backend.core.pipeline_task_manager import pipeline_manager
    job = pipeline_manager.get_job(job_id)
    if job:
        return {
            "job_id":   job.job_id,
            "status":   job.status.value if hasattr(job.status, 'value') else job.status,
            "progress": job.progress_pct,
            "result":   job.result or {},
            "error":    job.error,
        }

    # Fallback to checking segregation/enrichment jobs in job_registry
    from backend.workers.queue_executor import job_registry
    from backend.core.workspace_registry import registry
    qjob = job_registry.get_job(job_id)
    if qjob:
        status = qjob.get("status")
        result_payload = {}
        if status == "COMPLETED":
            # Find the context that owns this job to get the lineage tree
            for cid, ctx in registry.workspaces.items():
                if getattr(ctx, "active_job_id", None) == job_id:
                    if hasattr(ctx, "active_lineage") and ctx.active_lineage:
                        result_payload["lineage"] = ctx.active_lineage
                    break
        # Pull live telemetry from the in-memory tracker if job is still running
        from backend.workers.queue_executor import active_tracker
        tracker_data = {}
        live_tracker = active_tracker.get(job_id)
        if live_tracker:
            tracker_data = live_tracker.calculate_telemetry(live_tracker.rows_processed)

        return {
            "job_id": job_id,
            "status": status,
            "progress": qjob.get("progress", 0),
            "speed": qjob.get("compounds_per_sec", tracker_data.get("items_per_sec", 0)),
            "eta": qjob.get("eta_seconds", tracker_data.get("eta_seconds", 0)),
            "phase": tracker_data.get("phase", ""),
            "logs": tracker_data.get("logs", []),
            "result": result_payload,
            "error": qjob.get("error")
        }

    raise HTTPException(status_code=404, detail="Job not found")


@app.get("/api/jobs/{client_id}/download_enriched_parquet")
async def api_download_enriched_parquet(client_id: str, job_id: str = None):
    from backend.workers.task_manager import TaskManager
    from backend.core.workspace_registry import registry
    import os
    
    path = None
    if job_id:
        try:
            status = TaskManager.query_status(job_id)
            if status:
                path = status.get("result_path")
        except Exception:
            pass
            
    if not path:
        context = registry.get_context(client_id)
        path = context.descriptor_dataframe_path or context.parquet_path
        
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Enriched dataset not found")
        
    return FileResponse(
        path=path,
        media_type="application/octet-stream",
        filename=os.path.basename(path)
    )

@app.get("/api/jobs/{client_id}/compound_preview")
async def api_compound_preview(client_id: str, query: str, job_id: str = None):
    from backend.workers.task_manager import TaskManager
    from backend.core.workspace_registry import registry
    from backend.api.routes.modeling_routes import _resolve_columns
    from backend.core.pipeline_controller import _sanitize_for_json
    import os
    import pandas as pd
    import numpy as np
    
    path = None
    if job_id:
        try:
            status = TaskManager.query_status(job_id)
            if status:
                path = status.get("result_path")
        except Exception:
            pass
            
    context = registry.get_context(client_id)
    if not path:
        path = context.descriptor_dataframe_path or context.parquet_path
        
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Enriched dataset not found")
        
    try:
        df = pd.read_parquet(path)
        query_lower = query.lower()
        
        # Determine search columns
        mappings = context.mappings or {}
        smiles_col, val_col, unit_col, ep_col, descriptor_cols = _resolve_columns(df, mappings)
        
        # Search by SMILES or object columns (e.g. Chemical_Name, CAS)
        str_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
        
        match_idx = -1
        for col in str_cols:
            if match_idx != -1: break
            # exact match first, then substring
            matches = df[col].astype(str).str.lower()
            exact = matches == query_lower
            if exact.any():
                match_idx = exact.idxmax()
                break
            contains = matches.str.contains(query_lower, na=False)
            if contains.any():
                match_idx = contains.idxmax()
                break
                
        if match_idx == -1:
            return {"found": False, "message": f"Compound '{query}' not found in the dataset."}
            
        row = df.loc[match_idx]
        
        # Extract meta
        meta = {
            "SMILES": row[smiles_col] if smiles_col and smiles_col in row else "N/A",
            "Target Endpoint": f"{row[val_col]} {row[unit_col] if unit_col and unit_col in row else ''}".strip() if val_col and val_col in row else "N/A",
            "Matched Name/ID": row[str_cols[0]] if str_cols else "Unknown" # Best guess name
        }
        
        # Extract top dynamic descriptors
        descs = {}
        for d in descriptor_cols:
            val = row[d]
            if pd.notnull(val) and abs(val) > 0.0001:
                descs[d] = float(val)
                
        # Sort and take top 15 most prominent for visualization
        sorted_descs = dict(sorted(descs.items(), key=lambda item: abs(item[1]), reverse=True)[:15])
        
        result = {
            "found": True,
            "meta": meta,
            "descriptors": [{"name": k, "value": v} for k, v in sorted_descs.items()]
        }
        
        return _sanitize_for_json(result)
        
    except Exception as e:
        logger.error(f"Failed to query compound: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error searching dataset")


# ── SYSTEM TELEMETRY ───────────────────────────────────────
@app.get("/api/system/telemetry")
async def api_system_telemetry():
    from backend.core.pipeline_task_manager import pipeline_manager
    metrics = pipeline_manager.get_system_metrics()
    metrics["ws_connections"] = ws_broadcaster.connection_count()
    return metrics

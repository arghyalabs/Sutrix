# -----------------------------------------------------------------------------
# Scientific Data Orchestrator (SDO)
# Copyright (c) 2026. All Rights Reserved.
# Licensed under the PolyForm Noncommercial License 1.0.0.
# -----------------------------------------------------------------------------
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
from backend.parallel.chunk_scheduler import determine_optimal_scheduler_limits, split_into_batches
from backend.parallel.rdkit_worker import calculate_batch_worker

logger = logging.getLogger("sdo.backend.parallel.pool")

def calculate_descriptors_multiprocess(
    smiles_list: List[str],
    mode: str = "fast",
    include_mordred: bool = False,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    selected_descriptors: List[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Orchestrates CPU-bound descriptor calculations.
    
    Uses ThreadPoolExecutor (GIL-releasing via RDKit C++ internals) as the
    primary engine because ProcessPoolExecutor is unreliable when spawned
    from within an asyncio thread-pool executor on Windows (bootstrap error).
    Falls back to synchronous calculation if threading also fails.
    
    Progress callback fires per-compound (not per-chunk) for smooth UI updates.
    """
    results = {}
    if not smiles_list:
        return results

    total_count = len(smiles_list)
    
    # Determine optimal concurrency settings
    workers, chunk_size = determine_optimal_scheduler_limits(total_count)
    
    # Split dataset into sub-batches
    chunks = split_into_batches(smiles_list, chunk_size)
    logger.info(f"Submitting {len(chunks)} chunks to ThreadPoolExecutor (Workers={workers}, chunk_size={chunk_size}, selected={selected_descriptors})")
    
    completed_compounds = 0

    def _fire_callback(count):
        """Fire progress callback safely, suppressing cancellation signals."""
        nonlocal completed_compounds
        completed_compounds = count
        if progress_callback:
            try:
                progress_callback(min(count, total_count), total_count)
            except Exception as cb_err:
                logger.warning(f"Progress callback error: {cb_err}")
                raise  # Re-raise so cancellation propagates

    # ── Primary: ThreadPoolExecutor ───────────────────────────────────────────
    # RDKit's C++ core releases the GIL during heavy computation, so threads
    # give real parallelism without the Windows multiprocessing bootstrap issue.
    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_chunk = {
                executor.submit(calculate_batch_worker, chunk, include_mordred, mode, selected_descriptors): chunk
                for chunk in chunks
            }
            
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result()
                    # Fire callback PER COMPOUND for granular UI progress
                    for smiles, res in chunk_results:
                        results[smiles] = res
                        completed_compounds += 1
                        _fire_callback(completed_compounds)
                except Exception as e:
                    logger.error(f"Thread worker crashed for chunk of {len(chunk)}: {str(e)}")
                    for smiles in chunk:
                        results[smiles] = {
                            "success": False,
                            "error": f"THREAD_CRASHED: {str(e)}",
                            "data": {}
                        }
                        completed_compounds += 1
                        _fire_callback(completed_compounds)
                        
    except Exception as pool_err:
        logger.error(f"ThreadPoolExecutor failed: {pool_err}. Falling back to synchronous calculation.")
        # ── Final fallback: synchronous single-threaded loop ──────────────────
        from backend.parallel.rdkit_worker import compute_smiles_descriptors
        for smiles in smiles_list:
            try:
                results[smiles] = compute_smiles_descriptors(smiles, include_mordred, mode, selected_descriptors)
            except Exception as fe:
                results[smiles] = {"success": False, "error": f"FALLBACK_FAILED: {fe}", "data": {}}
            completed_compounds += 1
            _fire_callback(completed_compounds)
                
    return results

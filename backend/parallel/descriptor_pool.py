# -----------------------------------------------------------------------------
# Scientific Data Orchestrator (SDO)
# Copyright (c) 2026. All Rights Reserved.
# Licensed under the PolyForm Noncommercial License 1.0.0.
# -----------------------------------------------------------------------------
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
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
    Orchestrates CPU-bound descriptor calculations using a ProcessPoolExecutor.
    Splits compound lists into adaptive batches to bypass Python's GIL.
    """
    results = {}
    if not smiles_list:
        return results

    total_count = len(smiles_list)
    
    # 1. Determine optimal concurrency settings based on CPU cores & live RAM
    workers, chunk_size = determine_optimal_scheduler_limits(total_count)
    
    # 2. Slice dataset into sub-batches
    chunks = split_into_batches(smiles_list, chunk_size)
    logger.info(f"Submitting {len(chunks)} parallel execution chunks to ProcessPoolExecutor (Workers={workers})")
    
    completed_compounds = 0
    
    # 3. Spin up ProcessPoolExecutor
    # Note: Using fork/spawn safely on Windows/Linux environments
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_chunk = {
                executor.submit(calculate_batch_worker, chunk, include_mordred, mode, selected_descriptors): chunk
                for chunk in chunks
            }
            
            for future in as_completed(future_to_chunk):
                chunk = future_to_chunk[future]
                try:
                    chunk_results = future.result()
                    # Aggregate results
                    for smiles, res in chunk_results:
                        results[smiles] = res
                except Exception as e:
                    logger.error(f"Process worker crashed while calculating chunk: {str(e)}")
                    # Fault tolerance: Populate errors for compounds in the crashed chunk
                    for smiles in chunk:
                        results[smiles] = {
                            "success": False,
                            "error": f"PROCESS_CRASHED: {str(e)}",
                            "data": {}
                        }
                
                # Update progress counter dynamically
                completed_compounds += len(chunk)
                if progress_callback:
                    try:
                        progress_callback(min(completed_compounds, total_count), total_count)
                    except Exception as cb_err:
                        logger.warning(f"Error in progress callback: {cb_err}")
                        
    except Exception as pool_err:
        logger.error(f"Critical error setting up ProcessPoolExecutor: {pool_err}")
        # Fallback to synchronous loop if pool creation fails (fail-safe fallback)
        logger.info("Executing fail-safe synchronous descriptor processing...")
        for smiles in smiles_list:
            try:
                from backend.parallel.rdkit_worker import compute_smiles_descriptors
                results[smiles] = compute_smiles_descriptors(smiles, include_mordred, mode)
            except Exception as fe:
                results[smiles] = {"success": False, "error": f"FALLBACK_FAILED: {fe}", "data": {}}
                
    return results


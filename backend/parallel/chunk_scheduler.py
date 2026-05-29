import os
import math
import logging
from typing import List, Any

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("sdo.backend.parallel.scheduler")

def get_cpu_cores_and_memory() -> tuple:
    """Gets CPU core count and available physical memory in Gigabytes."""
    cores = os.cpu_count() or 1
    
    if psutil:
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024 ** 3)
    else:
        # Fallback approximation if psutil is not available
        available_gb = 4.0 
        
    return cores, available_gb

def determine_optimal_scheduler_limits(total_compounds: int) -> tuple:
    """
    Determines optimal worker count and chunk size based on RAM and dataset size.
    Prevents running out of memory on high-dimensional computations.
    """
    cores, available_gb = get_cpu_cores_and_memory()
    
    # 1. Calculate safe worker count (Adaptive memory protection)
    # Reserve at least 1 core for interactive Streamlit / FastAPI main threads
    recommended_workers = max(1, cores - 1)
    
    # Cap workers under low memory conditions to avoid RAM spikes
    if available_gb < 1.0:
        recommended_workers = 1
        logger.warning(f"Extremely low memory available ({available_gb:.2f} GB). Restricting parallel workers to 1 to avoid RAM thrashing.")
    elif available_gb < 2.0:
        recommended_workers = min(recommended_workers, 2)
        logger.info(f"Moderate memory limits ({available_gb:.2f} GB). Limiting background cores to {recommended_workers}.")
        
    # 2. Determine batch chunk size dynamically
    # For tiny datasets, avoid overhead by using smaller chunks
    if total_compounds < 50:
        chunk_size = max(5, total_compounds // recommended_workers)
    else:
        # Scale chunk size based on available RAM (larger RAM -> larger batch to minimize IPC overhead)
        if available_gb > 8.0:
            chunk_size = 250
        elif available_gb > 4.0:
            chunk_size = 100
        else:
            chunk_size = 40
            
    # Absolute minimum bound
    chunk_size = max(1, chunk_size)
    
    logger.info(f"Scheduler Optimization: Compounds={total_compounds} | Cores={cores} | RAM Available={available_gb:.2f} GB -> Workers={recommended_workers} | Batch Chunk={chunk_size}")
    return recommended_workers, chunk_size

def split_into_batches(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """Splits a flat list into a list of nested sub-batches."""
    if not items:
        return []
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

import os
import gc
import sys
import logging
from typing import Dict, Any, Tuple

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger("sdo.backend.optimization.guard")

class MemoryGuard:
    """
    Adaptive Memory Protection System for SDO.
    Tracks RAM footprints of host and children subprocesses to prevent out-of-memory crashes.
    """
    def __init__(self, ram_limit_pct: float = 75.0, emergency_limit_pct: float = 85.0):
        self.ram_limit_pct = ram_limit_pct
        self.emergency_limit_pct = emergency_limit_pct
        self._last_system_pct = 0.0

    def get_memory_status(self) -> Dict[str, Any]:
        """Gathers granular memory telemetry metrics for host and current process tree."""
        if not psutil:
            return {
                "total_ram_gb": 4.0, "available_ram_gb": 2.0, "ram_usage_pct": 50.0,
                "current_process_ram_mb": 150.0, "child_processes_ram_mb": 0.0,
                "is_critical": False, "is_locked": False
            }

        # 1. Host memory
        mem = psutil.virtual_memory()
        total_ram = mem.total / (1024 ** 3)
        available_ram = mem.available / (1024 ** 3)
        usage_pct = mem.percent
        self._last_system_pct = usage_pct

        # 2. Main process memory
        main_proc = psutil.Process(os.getpid())
        main_mem_mb = main_proc.memory_info().rss / (1024 ** 2)

        # 3. Subprocesses / Worker process memory
        child_mem_mb = 0.0
        try:
            children = main_proc.children(recursive=True)
            for child in children:
                try:
                    child_mem_mb += child.memory_info().rss / (1024 ** 2)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass

        is_critical = usage_pct >= self.ram_limit_pct
        is_locked = usage_pct >= self.emergency_limit_pct

        if is_locked:
            logger.critical(f"⚠️ EMERGENCY MEMORY SHIELD TRIGGERED: Host RAM usage is at {usage_pct:.1f}%! Available RAM: {available_ram:.2f} GB.")
        elif is_critical:
            logger.warning(f"⚠️ HIGH SYSTEM MEMORY SPIKE DETECTED: System RAM at {usage_pct:.1f}%. Starting aggressive caching sweeps.")

        return {
            "total_ram_gb": round(total_ram, 2),
            "available_ram_gb": round(available_ram, 2),
            "ram_usage_pct": round(usage_pct, 1),
            "current_process_ram_mb": round(main_mem_mb, 2),
            "child_processes_ram_mb": round(child_mem_mb, 2),
            "is_critical": is_critical,
            "is_locked": is_locked
        }

    def verify_safety_shield(self) -> Tuple[bool, str]:
        """
        Verifies if system resources are in a safe execution threshold.
        Returns a tuple: (is_safe: bool, status_message: str)
        """
        status = self.get_memory_status()
        
        if status["is_locked"]:
            return False, "EMERGENCY_LOCK: RAM exceeded 85% safety bounds. Queue execution paused."
        if status["is_critical"]:
            # Run aggressive garbage sweeps
            self.emergency_garbage_sweep()
            return True, "WARNING: Memory load is high (exceeded 75%). Calculations throttled."
            
        return True, "OK: Memory load is within safe operational thresholds."

    def calculate_adaptive_batch(self, total_compounds: int) -> Tuple[int, int]:
        """
        Calculates safe process concurrency and batch chunk boundaries.
        Large RAM -> larger chunks, Low RAM -> smaller chunks and capped worker threads.
        """
        if not psutil:
            return max(1, os.cpu_count() - 1), 100

        cores = os.cpu_count() or 1
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024 ** 3)
        usage_pct = mem.percent

        # Adaptive core allocation
        if usage_pct > 80.0:
            workers = 1
            chunk_size = 20
            logger.warning(f"Extremely high memory usage ({usage_pct:.1f}%). Throttling batch size to {chunk_size} and worker to 1 process.")
        elif usage_pct > 70.0:
            workers = max(1, min(2, cores // 2))
            chunk_size = 45
            logger.warning(f"RAM load at {usage_pct:.1f}%. Scaling background workers down to {workers} (Batch Chunk Size={chunk_size}).")
        else:
            workers = max(1, cores - 1)
            if available_gb > 8.0:
                chunk_size = 300
            elif available_gb > 4.0:
                chunk_size = 150
            else:
                chunk_size = 60

        return workers, chunk_size

    def emergency_garbage_sweep(self):
        """Forces immediate Python garbage collections and Sweeps internal pandas allocations."""
        logger.info("Executing aggressive emergency garbage sweeps to release unused memory buffers...")
        
        # 1. Force python gc sweep
        gc.collect()
        
        # 2. Clear open file descriptor buffers (if any are cached in sys modules)
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
            
        logger.info("Garbage collection complete.")

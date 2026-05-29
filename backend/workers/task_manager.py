import logging
import pandas as pd
from typing import Dict, Any, List
from backend.workers.queue_executor import task_queue, job_registry

logger = logging.getLogger("sdo.backend.workers.manager")

class TaskManager:
    """
    Client-facing manager to interact with the background worker queues.
    Submits calculations, queries job progress, and issues cancel commands.
    """
    @staticmethod
    def submit_enrichment(
        df: pd.DataFrame,
        mappings: Dict[str, str],
        selected_descriptors: List[str],
        include_mordred: bool = False,
        mode: str = "fast",
        workspace_id: str = None
    ) -> str:
        """Submits a long-running chemical descriptors enrichment task to background queue."""
        
        # 1. Create a task entry inside SQLite Job Registry
        job_id = job_registry.create_job()
        if not job_id:
            logger.error("Failed to generate task entry inside Job Registry.")
            return ""

        # 2. Package task payload
        payload = {
            "type": "enrichment",
            "df": df,
            "mappings": mappings,
            "selected_descriptors": selected_descriptors,
            "include_mordred": include_mordred,
            "mode": mode,
            "workspace_id": workspace_id
        }

        # 3. Queue task in asyncio.Queue
        # Submitting to queue instantly returns job ID back to API controllers
        task_queue.put_nowait((job_id, payload))
        logger.info(f"Successfully queued enrichment task '{job_id}' (State = QUEUED)")
        
        return job_id

    @staticmethod
    def submit_segregation(
        context_id: str,
        df: pd.DataFrame,
        hierarchy: List[str],
        enable_dedup: bool = False,
        enable_variance_pruning: bool = False,
        prune_high_variance: bool = False
    ) -> str:
        """Submits a graph builder segregation task."""
        job_id = job_registry.create_job()
        if not job_id:
            return ""

        payload = {
            "type": "segregation",
            "context_id": context_id,
            "df": df,
            "hierarchy": hierarchy,
            "enable_dedup": enable_dedup,
            "enable_variance_pruning": enable_variance_pruning,
            "prune_high_variance": prune_high_variance
        }

        task_queue.put_nowait((job_id, payload))
        logger.info(f"Successfully queued segregation task '{job_id}'")
        return job_id

    @staticmethod
    def query_status(job_id: str) -> Dict[str, Any]:
        """Queries the status, ETA, and progress of an active or completed background job."""
        job = job_registry.get_job(job_id)
        if not job:
            return {"job_id": job_id, "status": "NOT_FOUND", "progress": 0}
            
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": job["progress"],
            "eta_seconds": job["eta_seconds"],
            "compounds_per_sec": job["compounds_per_sec"],
            "result_path": job["result_path"],
            "error_message": job["error_message"],
            "created_at": job["created_at"],
            "completed_at": job["completed_at"]
        }

    @staticmethod
    def cancel_job(job_id: str) -> bool:
        """Interrupts a running background task and sets status to CANCELLED."""
        logger.info(f"Attempting to abort active background job: {job_id}")
        return job_registry.cancel_job(job_id)

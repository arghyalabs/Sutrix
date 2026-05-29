import os
import sqlite3
import time
import uuid
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("sdo.backend.workers.registry")

class JobRegistry:
    """
    SQLlite-backed Task Registry.
    Tracks background computational workflows and preserves task statuses.
    """
    def __init__(self, db_path: str = "sdo_jobs.db"):
        self.db_path = os.path.abspath(db_path)
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _initialize_db(self):
        """Creates jobs schema on startup."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        progress INTEGER DEFAULT 0,
                        eta_seconds REAL DEFAULT 0.0,
                        compounds_per_sec REAL DEFAULT 0.0,
                        result_path TEXT,
                        error_message TEXT,
                        created_at REAL NOT NULL,
                        completed_at REAL
                    )
                """)
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize Job Registry SQLite database: {e}")
        finally:
            conn.close()

    def create_job(self) -> str:
        """Creates a new job in the registry and returns its unique UUID."""
        job_id = str(uuid.uuid4())
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO jobs (job_id, status, progress, created_at)
                    VALUES (?, 'QUEUED', 0, ?)
                    """,
                    (job_id, time.time())
                )
            return job_id
        except sqlite3.Error as e:
            logger.error(f"Failed to insert new job record: {e}")
            return ""
        finally:
            conn.close()

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        eta: Optional[float] = None,
        speed: Optional[float] = None,
        result_path: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """Updates specific fields for an existing job in a thread-safe manner."""
        conn = self._get_connection()
        try:
            with conn:
                # Build dynamic query
                fields = []
                params = []
                
                if status is not None:
                    fields.append("status = ?")
                    params.append(status)
                    if status in ["COMPLETED", "FAILED", "CANCELLED"]:
                        fields.append("completed_at = ?")
                        params.append(time.time())
                if progress is not None:
                    fields.append("progress = ?")
                    params.append(progress)
                if eta is not None:
                    fields.append("eta_seconds = ?")
                    params.append(eta)
                if speed is not None:
                    fields.append("compounds_per_sec = ?")
                    params.append(speed)
                if result_path is not None:
                    fields.append("result_path = ?")
                    params.append(result_path)
                if error is not None:
                    fields.append("error_message = ?")
                    params.append(error)
                    
                if not fields:
                    return False
                    
                params.append(job_id)
                query = f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?"
                cur = conn.execute(query, params)
                return cur.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to update job '{job_id}': {e}")
            return False
        finally:
            conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves details of a single background computational job."""
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,)
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to fetch job record '{job_id}': {e}")
            return None
        finally:
            conn.close()

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Returns a list of all active (`QUEUED` or `RUNNING`) tasks in the pipeline."""
        conn = self._get_connection()
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM jobs WHERE status IN ('QUEUED', 'RUNNING') ORDER BY created_at ASC"
            )
            return [dict(r) for r in cur.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve active jobs: {e}")
            return []
        finally:
            conn.close()
            
    def cancel_job(self, job_id: str) -> bool:
        """Sets the state of a running or queued job to `CANCELLED`."""
        return self.update_job(job_id, status="CANCELLED", error="Cancelled by user instruction.")

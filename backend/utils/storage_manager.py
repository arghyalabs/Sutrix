import os
import shutil
import time
from typing import Dict, Any
from backend.storage.storage_manager import (
    StorageManager, UPLOADS_TEMP, OUTPUTS_TEMPORARY, LOW_STORAGE_LIMIT_BYTES, MAX_UPLOAD_SIZE_MB
)

_mgr = StorageManager()

def cleanup_temp_files() -> int:
    """Deletes old temporary uploads (>24 hours)."""
    return _mgr.clean_old_files(UPLOADS_TEMP, 24 * 3600)

def cleanup_old_outputs() -> int:
    """Deletes temporary exports older than 12 hours."""
    return _mgr.clean_old_files(OUTPUTS_TEMPORARY, 12 * 3600)

def cleanup_old_uploads() -> int:
    """Automatically sweeps workspace for stray debug files and orphans."""
    cleaned = 0
    for f in os.listdir("."):
        if f.endswith(".xlsx") and ("debug" in f.lower() or "snapshot" in f.lower() or "temp" in f.lower()):
            try:
                os.remove(f)
                cleaned += 1
            except Exception:
                pass
    return cleaned

def get_disk_usage() -> Dict[str, Any]:
    """Compiles active diagnostics from the centralized storage telemetry."""
    return _mgr.get_storage_diagnostics()

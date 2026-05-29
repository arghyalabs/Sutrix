import os
import shutil
import time
import sqlite3
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("sdo.backend.storage.storage_manager")

# Standardized folder hierarchy
UPLOADS_TEMP = os.path.join("uploads", "temp")
UPLOADS_ACTIVE = os.path.join("uploads", "active")
UPLOADS_ARCHIVE = os.path.join("uploads", "archive")

OUTPUTS_ACTIVE = os.path.join("outputs", "active")
OUTPUTS_ARCHIVED = os.path.join("outputs", "archived")
OUTPUTS_TEMPORARY = os.path.join("outputs", "temporary")
OUTPUTS_REPORTS = os.path.join("outputs", "reports")

DISK_CACHE_DIR = os.path.join("backend", "cache", "mol_svg_cache")
DB_PATH = "sutrix_science.db"

# Storage Configuration
MAX_SVG_CACHE_SIZE_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB
LOW_STORAGE_LIMIT_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
MAX_UPLOAD_SIZE_MB = 100  # 100 MB max file size upload limit

class StorageManager:
    """
    Enterprise storage coordinator for temporary upload lifecycles,
    molecule visualization cache limits, and auto-cleanup triggers.
    """
    def __init__(self):
        self.initialize_directories()

    def initialize_directories(self):
        """Pre-creates all necessary directory hierarchies safely."""
        dirs = [
            UPLOADS_TEMP, UPLOADS_ACTIVE, UPLOADS_ARCHIVE,
            OUTPUTS_ACTIVE, OUTPUTS_ARCHIVED, OUTPUTS_TEMPORARY, OUTPUTS_REPORTS,
            DISK_CACHE_DIR
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def get_free_disk_space(self) -> int:
        """Gets free disk space in bytes for the workspace drive."""
        try:
            total, used, free = shutil.disk_usage(".")
            return free
        except Exception as e:
            logger.error(f"Failed to get disk space: {e}")
            return 100 * 1024 * 1024 * 1024  # Fallback to 100 GB if error

    def is_low_storage(self) -> bool:
        """Checks if free space is below the low storage limit (2 GB)."""
        return self.get_free_disk_space() < LOW_STORAGE_LIMIT_BYTES

    def get_directory_size(self, path: str) -> int:
        """Computes total size of files inside a directory in bytes."""
        total_size = 0
        if not os.path.exists(path):
            return 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size

    def clean_old_files(self, directory: str, retention_seconds: float) -> int:
        """Deletes files older than a retention threshold in seconds."""
        cleaned_count = 0
        now = time.time()
        if not os.path.exists(directory):
            return 0
            
        for f in os.listdir(directory):
            fp = os.path.join(directory, f)
            if os.path.isfile(fp):
                try:
                    mtime = os.path.getmtime(fp)
                    if (now - mtime) > retention_seconds:
                        os.remove(fp)
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete old file {fp}: {e}")
        return cleaned_count

    def run_automatic_cleanup(self) -> Dict[str, Any]:
        """
        Executes automatic retention pruning:
        - Temp uploads older than 24h deleted.
        - Temp output exports older than 12h deleted.
        - Redundant debug pre-export snapshots deleted.
        """
        self.initialize_directories()
        
        # 1. Prune temporary uploads (> 24 hours)
        cleaned_uploads = self.clean_old_files(UPLOADS_TEMP, 24 * 3600)
        
        # 2. Prune temporary exports (> 12 hours)
        cleaned_outputs = self.clean_old_files(OUTPUTS_TEMPORARY, 12 * 3600)
        
        # 3. Scan and remove debug excel spreadsheets in workspace root
        cleaned_debug = 0
        for f in os.listdir("."):
            if f.endswith(".xlsx") and ("debug" in f.lower() or "snapshot" in f.lower() or "temp" in f.lower()):
                try:
                    os.remove(f)
                    cleaned_debug += 1
                except Exception:
                    pass

        # 4. Prune visual SVG cache if it exceeds size limits
        pruned_cache = self.prune_svg_cache_if_needed()

        return {
            "cleaned_uploads": cleaned_uploads,
            "cleaned_outputs": cleaned_outputs,
            "cleaned_debug_files": cleaned_debug,
            "pruned_cache_files": pruned_cache,
            "low_storage_mode": self.is_low_storage()
        }

    def prune_svg_cache_if_needed(self) -> int:
        """
        Prunes the dual-layer visual cache if it exceeds 1 GB.
        Deletes the oldest LRU SVG renderings by checking render_timestamp.
        """
        current_size = self.get_directory_size(DISK_CACHE_DIR)
        if current_size <= MAX_SVG_CACHE_SIZE_BYTES:
            return 0

        logger.info("SVG render cache exceeds 1 GB. Initiating LRU cache pruning...")
        pruned_count = 0
        
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Find cached items ordered by rendering timestamp oldest first
                cursor.execute(
                    "SELECT canonical_smiles, width, height, svg_string FROM molecule_svg_cache ORDER BY render_timestamp ASC"
                )
                rows = cursor.fetchall()
                
                # Prune until under 70% of max threshold for hysteresis efficiency
                target_size = MAX_SVG_CACHE_SIZE_BYTES * 0.7
                temp_size = current_size
                
                for row in rows:
                    smiles, w, h, svg = row
                    # Calculate approximate string size in bytes
                    svg_len = len(svg.encode('utf-8'))
                    
                    # Delete from SQLite
                    conn.execute(
                        "DELETE FROM molecule_svg_cache WHERE canonical_smiles = ? AND width = ? AND height = ?",
                        (smiles, w, h)
                    )
                    
                    # Delete from Disk Cache
                    import hashlib
                    hash_input = f"{smiles.strip()}_{w}_{h}".encode('utf-8')
                    file_hash = hashlib.sha256(hash_input).hexdigest()
                    disk_path = os.path.join(DISK_CACHE_DIR, f"{file_hash}.svg")
                    
                    if os.path.exists(disk_path):
                        try:
                            file_size = os.path.getsize(disk_path)
                            os.remove(disk_path)
                            temp_size -= file_size
                        except Exception:
                            temp_size -= svg_len
                    else:
                        temp_size -= svg_len
                        
                    pruned_count += 1
                    if temp_size <= target_size:
                        break
                        
                conn.commit()
        except Exception as e:
            logger.error(f"Error during LRU SVG cache pruning: {e}")
            
        return pruned_count

    def get_storage_diagnostics(self) -> Dict[str, Any]:
        """Compiles standard telemetry regarding current space usage."""
        free = self.get_free_disk_space()
        
        # Calculate individual folder sizes
        svg_cache_size = self.get_directory_size(DISK_CACHE_DIR)
        temp_uploads_size = self.get_directory_size(UPLOADS_TEMP)
        exports_size = (
            self.get_directory_size(OUTPUTS_ACTIVE) + 
            self.get_directory_size(OUTPUTS_TEMPORARY) +
            self.get_directory_size(OUTPUTS_REPORTS)
        )
        
        # Estimate log storage size
        logs_size = 0
        if os.path.exists("logs"):
            logs_size = self.get_directory_size("logs")
        elif os.path.exists("app.log"):
            logs_size = os.path.getsize("app.log")

        return {
            "free_space_gb": free / (1024 ** 3),
            "free_space_raw": free,
            "svg_cache_mb": svg_cache_size / (1024 ** 2),
            "temp_uploads_mb": temp_uploads_size / (1024 ** 2),
            "exports_mb": exports_size / (1024 ** 2),
            "logs_mb": logs_size / (1024 ** 2),
            "low_storage_warning": free < LOW_STORAGE_LIMIT_BYTES
        }

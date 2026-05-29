import os
import json
import hashlib
from typing import Dict, Any, Optional

class CacheManager:
    """
    Smart caching layer for the Statistical Engine.
    Uses SHA256 hashes of the dataset state to enable instant reloading 
    of identical hierarchy + filter combinations, bypassing heavy pandas processing.
    """
    
    @staticmethod
    def _get_cache_dir(workspace_id: str) -> str:
        return os.path.join("backend", "workspaces", workspace_id, "cache")
        
    @classmethod
    def generate_hash(cls, pipeline_version: str, dataset_version: str, active_branch: str, filters: Dict[str, str], requested_columns: list) -> str:
        """Generates a reproducible SHA256 hash for the requested state."""
        state_dict = {
            "v": pipeline_version,
            "d": dataset_version,
            "b": active_branch,
            "f": filters,
            "c": requested_columns
        }
        # Sort keys to ensure deterministic hashing
        state_str = json.dumps(state_dict, sort_keys=True)
        return hashlib.sha256(state_str.encode('utf-8')).hexdigest()
        
    @classmethod
    def get_cached_result(cls, workspace_id: str, state_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves a cached JSON response if it exists."""
        cache_dir = cls._get_cache_dir(workspace_id)
        file_path = os.path.join(cache_dir, f"{state_hash}.json")
        
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    return json.load(f)
            except Exception:
                return None
        return None
        
    @classmethod
    def save_cached_result(cls, workspace_id: str, state_hash: str, data: Dict[str, Any]) -> None:
        """Saves a JSON response to the cache layer."""
        cache_dir = cls._get_cache_dir(workspace_id)
        os.makedirs(cache_dir, exist_ok=True)
        file_path = os.path.join(cache_dir, f"{state_hash}.json")
        
        try:
            with open(file_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            # Non-fatal, just log in production
            pass


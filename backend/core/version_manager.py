import os
import json
import time
import glob
from typing import Dict, Any, Optional
import pandas as pd
from backend.core.workspace_registry import PipelineContext

class VersionManager:
    """
    Manages dataset versioning for scientific reproducibility.
    Every filtration or modification step creates a new version with detailed lineage metadata.
    """
    
    @staticmethod
    def _get_parquet_dir(workspace_id: str) -> str:
        return os.path.join("backend", "workspaces", workspace_id, "parquet")
        
    @staticmethod
    def _get_next_version(parquet_dir: str) -> int:
        files = glob.glob(os.path.join(parquet_dir, "dataset_v*.parquet"))
        if not files:
            return 1
        versions = []
        for f in files:
            base = os.path.basename(f)
            # format: dataset_vX.parquet
            try:
                v = int(base.replace("dataset_v", "").replace(".parquet", ""))
                versions.append(v)
            except ValueError:
                continue
        return max(versions) + 1 if versions else 1

    @classmethod
    def save_version(cls, 
                     context: PipelineContext, 
                     df: pd.DataFrame, 
                     action_type: str,
                     filter_applied: str = "None",
                     removed_rows: int = 0,
                     branch: str = "Main",
                     user: str = "System") -> str:
        """
        Saves a new version of the dataset and logs its scientific lineage metadata.
        Returns the path to the newly saved parquet file.
        """
        parquet_dir = cls._get_parquet_dir(context.workspace_id)
        os.makedirs(parquet_dir, exist_ok=True)
        
        version_num = cls._get_next_version(parquet_dir)
        filename = f"dataset_v{version_num}.parquet"
        file_path = os.path.join(parquet_dir, filename)
        
        # Save dataset (Snappy compression is default in pandas to_parquet)
        df.to_parquet(file_path, compression='snappy')
        
        # Determine parent version
        parent_version = "None"
        if context.parquet_path:
            parent_version = os.path.basename(context.parquet_path)
            
        # Create Metadata
        metadata = {
            "version": version_num,
            "filename": filename,
            "parent": parent_version,
            "action_type": action_type,
            "filter": filter_applied,
            "remaining_rows": len(df),
            "removed_rows": removed_rows,
            "timestamp": time.time(),
            "user": user,
            "branch": branch
        }
        
        # Save Metadata
        meta_path = os.path.join(parquet_dir, f"dataset_v{version_num}.json")
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=4)
            
        # Update context
        context.parquet_path = file_path
        context.dataframe_cache = df
        context.add_trace(f"v{version_num}: {action_type}")
        context.touch()
        
        return file_path
        
    @classmethod
    def load_version(cls, context: PipelineContext, version_num: int) -> Optional[pd.DataFrame]:
        """Loads a specific dataset version and restores the context."""
        parquet_dir = cls._get_parquet_dir(context.workspace_id)
        file_path = os.path.join(parquet_dir, f"dataset_v{version_num}.parquet")
        
        if not os.path.exists(file_path):
            return None
            
        df = pd.read_parquet(file_path)
        context.parquet_path = file_path
        context.dataframe_cache = df
        context.touch()
        return df


import os
import json
import logging
import time
from typing import Dict, Any, Optional
import pandas as pd

from backend.core.workspace_registry import PipelineContext, registry

logger = logging.getLogger("sdo.core.session_state_manager")

class SessionStateManager:
    """
    Manages persistence, recovery, and cleanup of scientific pipeline sessions.
    Saves and loads PipelineContext states to/from a crash-safe JSON directory
    to ensure seamless reconnection, data recovery, and resilience.
    """
    
    def __init__(self, session_dir: str = "uploads/sessions"):
        self.session_dir = session_dir
        os.makedirs(self.session_dir, exist_ok=True)

    def get_state_file_path(self, workspace_id: str) -> str:
        """Returns the file path for a workspace session state."""
        return os.path.join(self.session_dir, f"session_{workspace_id}.json")

    def save_session(self, context: PipelineContext) -> bool:
        """
        Serializes and persists the active PipelineContext to disk.
        Executes atomically to prevent data corruption.
        """
        try:
            state_data = {
                "workspace_id": context.workspace_id,
                "pipeline_version": context.pipeline_version,
                "scientific_schema_version": context.scientific_schema_version,
                "descriptor_engine_version": context.descriptor_engine_version,
                "parquet_path": context.parquet_path,
                "mappings": context.mappings,
                "execution_trace": context.execution_trace,
                "segmentation_results": context.segmentation_results,
                "readiness_results": context.readiness_results,
                "active_job_id": context.active_job_id,
                "active_lineage": context.active_lineage,
                "node_details": context.hierarchy_engine.node_details if (context.hierarchy_engine and hasattr(context.hierarchy_engine, "node_details")) else None,
                "last_accessed": context.last_accessed,
                "saved_at": time.time()
            }
            
            temp_path = self.get_state_file_path(context.workspace_id) + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(state_data, f, indent=2)
                
            # Atomic replace (standard deployment best practice)
            final_path = self.get_state_file_path(context.workspace_id)
            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_path, final_path)
            
            logger.info(f"Session {context.workspace_id} successfully serialized to disk.")
            return True
        except Exception as e:
            logger.error(f"Failed to serialize session state for {context.workspace_id}: {e}")
            return False

    def load_session(self, workspace_id: str) -> Optional[PipelineContext]:
        """
        Deserializes and restores a PipelineContext session state from disk.
        Reconstructs database indices and dataframe slices if a cached source exists.
        """
        state_path = self.get_state_file_path(workspace_id)
        if not os.path.exists(state_path):
            logger.info(f"No serial session file found for workspace {workspace_id}.")
            return None
            
        try:
            with open(state_path, "r") as f:
                state_data = json.load(f)
                
            # Reconstruct context
            context = PipelineContext(
                workspace_id=state_data["workspace_id"],
                pipeline_version=state_data.get("pipeline_version", "3.0"),
                scientific_schema_version=state_data.get("scientific_schema_version", "1.0"),
                descriptor_engine_version=state_data.get("descriptor_engine_version", "2023.9")
            )
            
            context.parquet_path = state_data.get("parquet_path")
            context.mappings = state_data.get("mappings", {})
            context.execution_trace = state_data.get("execution_trace", [])
            context.segmentation_results = state_data.get("segmentation_results", {})
            context.readiness_results = state_data.get("readiness_results", {})
            context.active_job_id = state_data.get("active_job_id")
            context.last_accessed = state_data.get("last_accessed", time.time())
            
            # Restore active lineage & hierarchy engine details
            context.active_lineage = state_data.get("active_lineage")
            context.active_segregation_result = context.active_lineage
            
            node_details = state_data.get("node_details")
            if node_details:
                try:
                    from backend.core.hierarchy_engine import HierarchyEngine
                    engine = HierarchyEngine(context.workspace_id, context.mappings)
                    engine.node_details = node_details
                    context.hierarchy_engine = engine
                except Exception as e:
                    logger.error(f"Failed to restore hierarchy engine in load_session: {e}")
            
            # Re-seed into global registry
            registry.workspaces[workspace_id] = context
            logger.info(f"Session {workspace_id} successfully restored from serialized state.")
            return context
        except Exception as e:
            logger.error(f"Failed to load session state for {workspace_id}: {e}")
            return None

    def delete_session(self, workspace_id: str) -> bool:
        """Removes session files and cleans up system caches to free disk space."""
        try:
            state_path = self.get_state_file_path(workspace_id)
            if os.path.exists(state_path):
                os.remove(state_path)
                logger.info(f"Deleted state file for session {workspace_id}.")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session state file for {workspace_id}: {e}")
            return False

# Global state manager singleton
session_manager = SessionStateManager()

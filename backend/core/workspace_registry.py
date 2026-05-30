import os
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.hierarchy_engine import HierarchyEngine
import pandas as pd

logger = logging.getLogger("sdo.core.registry")

@dataclass
class PipelineSnapshot:
    stage: str
    timestamp: float
    parquet_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

@dataclass
class PipelineContext:
    workspace_id: str
    pipeline_version: str = "3.0"
    scientific_schema_version: str = "1.0"
    descriptor_engine_version: str = "2023.9"
    
    # Hybrid Model: Source of truth is Parquet, dataframe_cache holds only active slice
    parquet_path: Optional[str] = None
    dataframe_cache: Optional[pd.DataFrame] = None
    
    # Dataframe snapshots (Paths to parquet checkpoints to avoid heavy RAM utilization)
    raw_dataframe_path: Optional[str] = None
    mapped_dataframe_path: Optional[str] = None
    descriptor_dataframe_path: Optional[str] = None
    
    # Trace & Metadata
    mappings: Dict[str, str] = field(default_factory=dict)
    execution_trace: List[str] = field(default_factory=list)
    snapshots: List[PipelineSnapshot] = field(default_factory=list)
    
    # Derived results & outputs
    segmentation_results: Dict[str, Any] = field(default_factory=dict)
    readiness_results: Dict[str, Any] = field(default_factory=dict)
    export_paths: Dict[str, str] = field(default_factory=dict)
    active_job_id: Optional[str] = None
    active_segregation_result: Optional[Any] = None

    # ── Scientific Hierarchy / Lineage (populated after segregation) ──────────
    # Serialisable lineage dict: {nodes, edges, root_id, total_nodes, max_depth}
    active_hierarchy: List[str] = field(default_factory=list)
    active_lineage: Optional[Dict[str, Any]] = None
    # Live HierarchyEngine reference – holds precomputed node stats + charts
    # Typed as Any to avoid circular import at runtime
    hierarchy_engine: Optional[Any] = None
    
    # Fast search index for Google-style compound exploration
    search_index: Optional[List[Dict[str, Any]]] = None

    # Platform status telemetry and job tracking
    job_state: Dict[str, Any] = field(default_factory=dict)
    websocket_connections: List[str] = field(default_factory=list)
    telemetry: Dict[str, Any] = field(default_factory=dict)

    # Lifecycle
    last_accessed: float = field(default_factory=time.time)
    
    # Do NOT persist the lock across serialization; it's an asyncio construct
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    
    def __post_init__(self):
        """Initializes the dedicated storage tree for this workspace."""
        base_dir = os.path.join("workspaces", self.workspace_id)
        self.workspace_dir = base_dir
        dirs = ['uploads', 'exports', 'cache', 'lineage', 'logs']
        for d in dirs:
            os.makedirs(os.path.join(base_dir, d), exist_ok=True)
            
    def touch(self, save_to_disk: bool = False):
        self.last_accessed = time.time()
        if save_to_disk:
            try:
                from backend.core.session_state_manager import session_manager
                session_manager.save_session(self)
            except Exception as e:
                logger.debug(f"Circular session save deferred: {e}")
        
    def add_trace(self, action: str):
        self.execution_trace.append(action)
        self.touch(save_to_disk=True)
        
    def add_snapshot(self, stage: str, parquet_path: str, metadata: dict = None, warnings: list = None):
        self.snapshots.append(PipelineSnapshot(
            stage=stage,
            timestamp=time.time(),
            parquet_path=parquet_path,
            metadata=metadata or {},
            warnings=warnings or []
        ))
        self.touch(save_to_disk=True)
        
    def flush_memory(self):
        """Flushes the dataframe cache, hierarchy engine, and search index to free RAM (Hybrid Model)."""
        self.dataframe_cache = None
        self.search_index = None
        # Release the engine's in-memory node dataframe slices (already persisted to disk)
        if self.hierarchy_engine is not None:
            try:
                if hasattr(self.hierarchy_engine, "_node_df_slices"):
                    self.hierarchy_engine._node_df_slices.clear()
            except Exception:
                pass
        
    def load_slice(self) -> pd.DataFrame:
        """Loads dataframe from parquet source of truth."""
        self.touch()
        if self.dataframe_cache is not None:
            return self.dataframe_cache
        if not self.parquet_path or not os.path.exists(self.parquet_path):
            raise ValueError(f"No source of truth parquet found for workspace {self.workspace_id}")
        self.dataframe_cache = pd.read_parquet(self.parquet_path)
        return self.dataframe_cache

class WorkspaceRegistry:
    def __init__(self, ttl_seconds: int = 3600):
        self.workspaces: Dict[str, PipelineContext] = {}
        self.ttl_seconds = ttl_seconds
        # Throttle state-file mtime checks: store last-checked timestamp per workspace
        # so we never hit the filesystem more than once every 5 seconds per workspace.
        self._last_mtime_check: Dict[str, float] = {}
        self._MTIME_CHECK_INTERVAL = 5.0  # seconds

    def get_context(self, workspace_id: str) -> PipelineContext:
        from backend.core.session_state_manager import session_manager

        if workspace_id not in self.workspaces:
            # Workspace not in memory at all — load from disk
            try:
                loaded_ctx = session_manager.load_session(workspace_id)
                if loaded_ctx:
                    self.workspaces[workspace_id] = loaded_ctx
            except Exception:
                pass
            if workspace_id not in self.workspaces:
                self.workspaces[workspace_id] = PipelineContext(workspace_id=workspace_id)
        else:
            # Workspace is in memory. Only re-check disk if enough time has passed.
            now = time.time()
            last_check = self._last_mtime_check.get(workspace_id, 0.0)
            if now - last_check >= self._MTIME_CHECK_INTERVAL:
                self._last_mtime_check[workspace_id] = now
                try:
                    state_path = session_manager.get_state_file_path(workspace_id)
                    if os.path.exists(state_path):
                        mtime = os.path.getmtime(state_path)
                        # If the file was modified more recently than last_accessed,
                        # another process updated the session — reload it.
                        if mtime > self.workspaces[workspace_id].last_accessed + 0.5:
                            loaded_ctx = session_manager.load_session(workspace_id)
                            if loaded_ctx:
                                self.workspaces[workspace_id] = loaded_ctx
                except Exception:
                    pass  # Non-critical; keep using in-memory context

        context = self.workspaces[workspace_id]
        context.touch()
        return context


    def cleanup_expired(self):
        """Removes abandoned sessions to prevent memory leaks."""
        current_time = time.time()
        expired_keys = []
        for wid, ctx in self.workspaces.items():
            if (current_time - ctx.last_accessed) > self.ttl_seconds:
                expired_keys.append(wid)
                
        for wid in expired_keys:
            ctx = self.workspaces.pop(wid)
            ctx.flush_memory()
            
            # Clean up workspace temporary files
            import shutil
            workspace_dir = getattr(ctx, "workspace_dir", os.path.join("workspaces", wid))
            if os.path.exists(workspace_dir):
                try:
                    shutil.rmtree(workspace_dir)
                    logger.info(f"Workspace {wid} deleted temporary files from {workspace_dir}.")
                except Exception as e:
                    logger.error(f"Failed to delete workspace {wid} directory: {e}")
                    
            logger.info(f"Workspace {wid} TTL expired. Flushed from RAM and disk.")

registry = WorkspaceRegistry()

# Background task for TTL cleanup
async def registry_cleanup_loop():
    while True:
        await asyncio.sleep(600)  # run every 10 minutes
        registry.cleanup_expired()

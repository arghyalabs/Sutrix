"""
backend/core/lineage_builder.py

Thin orchestration wrapper around HierarchyEngine.
Responsible for: engine lifecycle, lineage construction, and node-detail retrieval.

Author: Scientific Data Orchestrator
"""

import logging
from typing import Any, Dict, Optional

from backend.core.hierarchy_engine import HierarchyEngine

logger = logging.getLogger("sdo.core.lineage_builder")


class LineageBuilder:
    """
    Stateless orchestrator for scientific lineage construction.

    All heavy computation is delegated to ``HierarchyEngine``.
    This class exists to provide a clean, testable entry-point used by
    ``queue_executor`` and any future pipeline stages.
    """

    @staticmethod
    def run(
        df,
        hierarchy_cols,
        mappings: dict,
        workspace_id: str,
        broadcast_fn=None,
    ) -> dict:
        """
        Orchestrate full lineage construction.

        Parameters
        ----------
        df : pd.DataFrame
            Post-dedup dataset.
        hierarchy_cols : list[str]
            Ordered column names that define the hierarchy depth.
        mappings : dict
            {user_col: scientific_role} mapping from workspace context.
        workspace_id : str
            Unique workspace / session identifier.
        broadcast_fn : callable | None
            Optional sync callback(event_dict) invoked after each node
            is built.  The async executor drains events separately.

        Returns
        -------
        dict
            Serialisable lineage payload (nodes, edges, root_id, …)
            ready for WebSocket JOB_COMPLETED broadcast.
        """
        import pandas as pd

        if not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError("LineageBuilder.run() requires a non-empty DataFrame.")

        if not hierarchy_cols:
            raise ValueError("hierarchy_cols must contain at least one column.")

        logger.info(
            f"[{workspace_id}] LineageBuilder starting: "
            f"{len(df)} rows, {len(hierarchy_cols)} hierarchy levels."
        )

        engine = HierarchyEngine(workspace_id=workspace_id, mappings=mappings)

        # Phase A: recursive tree construction + stats/chart precomputation
        lineage_data = engine.build(df, hierarchy_cols, broadcast_fn=broadcast_fn)

        # Phase B: persist node DataFrames to disk (parquet, csv, xlsx, feather, sdf)
        engine.save_node_dataframes(workspace_id)

        logger.info(
            f"[{workspace_id}] LineageBuilder complete: "
            f"{lineage_data['total_nodes']} nodes, "
            f"max depth {lineage_data['max_depth']}."
        )

        # Attach the engine reference onto the lineage dict so the
        # executor can store it in context.hierarchy_engine.
        lineage_data["_engine"] = engine

        return lineage_data

    @staticmethod
    def get_node_detail(
        workspace_id: str,
        node_id: str,
        engine_cache: Optional[Dict[str, Any]],
    ) -> dict:
        """
        Retrieve pre-computed node detail from an engine's node_details cache.

        Parameters
        ----------
        workspace_id : str
            Used only for logging.
        node_id : str
            The 12-char SHA node identifier.
        engine_cache : dict | None
            The ``HierarchyEngine.node_details`` dict, typically stored as
            ``context.hierarchy_engine.node_details``.

        Returns
        -------
        dict
            Full NodeDetail payload (metadata, stats, charts, export_formats).

        Raises
        ------
        KeyError
            If node_id is not found in the cache.
        ValueError
            If engine_cache is None (no segregation run yet).
        """
        if engine_cache is None:
            raise ValueError(
                f"[{workspace_id}] No hierarchy engine cache available. "
                "Run segregation first."
            )

        detail = engine_cache.get(node_id)
        if detail is None:
            raise KeyError(
                f"[{workspace_id}] Node '{node_id}' not found in hierarchy "
                f"engine cache. Available ids: {list(engine_cache.keys())[:10]}"
            )

        return detail

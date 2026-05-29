# -----------------------------------------------------------------------------
# Scientific Data Orchestrator (SDO)
# Copyright (c) 2026. All Rights Reserved.
# Licensed under the PolyForm Noncommercial License 1.0.0.
# -----------------------------------------------------------------------------
"""
backend/core/hierarchy_engine.py

Recursive dataframe branching engine for toxicological hierarchy construction.
Each node inherits its parent's filtered dataframe and applies ONE incremental
filter, computing statistics and precomputing chart payloads in-place.

Author: Scientific Data Orchestrator
"""

import os
import logging
import hashlib
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("sdo.core.hierarchy_engine")

# ── Scientific column role constants ────────────────────────────────────────
_POTENCY_ROLES = frozenset({
    "ic50", "ec50", "lc50", "ld50", "logp",
    "molecular_weight", "tpsa", "exposure_time",
})

_COMPOUND_ID_ROLES = frozenset({
    "canonical_smiles", "smiles", "cas_number", "chemical_id",
})


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HierarchyNode:
    """Lightweight metadata node for a single hierarchy branch."""

    id: str
    parent_id: Optional[str]
    level: int
    node_name: str           # human-readable label (val or "Root")
    filter_col: str          # column name used to filter
    filter_val: str          # value this node was filtered by
    applied_filter: Dict[str, str]    # {col: val} for this node's own split
    inherited_filters: Dict[str, str] # cumulative {col: val} from ancestors
    path: str                # "Root > Fish > LC50"
    row_count: int
    unique_compounds: int    # unique SMILES/CAS count in this node's slice
    is_leaf: bool
    children: List[str] = field(default_factory=list)  # child node ids


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class HierarchyEngine:
    """
    Recursive dataframe branching engine.

    Each node:
        1. Holds a filtered slice of the original DataFrame.
        2. Applies ONE incremental filter (one column + one value).
        3. Pre-computes lightweight stats and chart payloads stored in
           ``node_details`` (keyed by node id).

    The heavy node DataFrames are NOT stored in RAM after processing –
    they are written to Parquet via ``save_node_dataframes()``.
    """

    def __init__(self, workspace_id: str, mappings: Dict[str, str]):
        """
        Parameters
        ----------
        workspace_id : str
            Unique identifier for this workspace session.
        mappings : dict
            {user_column_name: scientific_role} e.g. {"Effect": "endpoint"}.
        """
        self.workspace_id = workspace_id
        self.mappings = mappings  # col_name -> sci_role

        # Inverted: sci_role -> col_name (first match wins)
        self._sci_to_col: Dict[str, str] = {}
        for col, role in mappings.items():
            if role not in self._sci_to_col:
                self._sci_to_col[role] = col

        self.nodes: Dict[str, HierarchyNode] = {}
        self.node_details: Dict[str, dict] = {}   # heavy stats + charts per node
        self._node_df_slices: Dict[str, pd.DataFrame] = {}  # transient, flushed after save

        self._total_nodes_built = 0
        self._broadcast_events: List[dict] = []   # accumulated for async drain

    # ── Public API ──────────────────────────────────────────────────────────

    def build(
        self,
        df: pd.DataFrame,
        hierarchy_cols: List[str],
        broadcast_fn: Optional[Callable] = None,
    ) -> dict:
        """
        Main entry point.

        1. Creates root node from the full dataframe.
        2. Recursively creates child nodes – each filtering the parent df.
        3. Pre-computes stats + charts per node.
        4. Returns serialisable lineage dict.

        Parameters
        ----------
        df : pd.DataFrame
            The full (post-dedup) dataset.
        hierarchy_cols : list[str]
            Ordered list of column names to split on, e.g.
            ["species_group", "endpoint", "exposure_duration"].
        broadcast_fn : callable | None
            Optional *sync* callback(event_dict) called after each node.
            The queue_executor drains these asynchronously.
        """
        if df is None or df.empty:
            raise ValueError("HierarchyEngine.build() received an empty DataFrame.")

        if not hierarchy_cols:
            raise ValueError("hierarchy_cols must have at least one column.")

        # Validate columns exist
        missing = [c for c in hierarchy_cols if c not in df.columns]
        if missing:
            raise ValueError(
                f"Hierarchy columns not found in DataFrame: {missing}. "
                f"Available: {list(df.columns)}"
            )

        logger.info(
            f"[{self.workspace_id}] Building hierarchy: "
            f"{len(df)} rows × {len(hierarchy_cols)} levels: {hierarchy_cols}"
        )

        # ── Root node ──────────────────────────────────────────────────────
        root_id = "root"
        next_col = hierarchy_cols[0] if hierarchy_cols else None

        root_node = HierarchyNode(
            id=root_id,
            parent_id=None,
            level=0,
            node_name="Root",
            filter_col="",
            filter_val="",
            applied_filter={},
            inherited_filters={},
            path="Root",
            row_count=len(df),
            unique_compounds=self._get_unique_compounds(df),
            is_leaf=(len(hierarchy_cols) == 0),
            children=[],
        )
        self.nodes[root_id] = root_node
        self._node_df_slices[root_id] = df

        root_stats = self._compute_node_stats(df)
        root_charts = self._precompute_charts(df, next_col)
        self.node_details[root_id] = {
            "id": root_id,
            "metadata": self._node_to_meta(root_node),
            "stats": root_stats,
            "charts": root_charts,
            "export_formats": self._export_formats(df),
        }

        if broadcast_fn:
            broadcast_fn({
                "phase": "Building hierarchy tree – Root",
                "active_node": "Root",
                "rows_remaining": len(df),
                "nodes_built": 1,
            })

        # ── Recursive build ────────────────────────────────────────────────
        self._build_recursive(
            df=df,
            hierarchy_cols=hierarchy_cols,
            parent_id=root_id,
            parent_path="Root",
            inherited_filters={},
            level=1,
            broadcast_fn=broadcast_fn,
        )

        logger.info(
            f"[{self.workspace_id}] Hierarchy complete: "
            f"{len(self.nodes)} nodes across {self._max_depth()} levels."
        )
        return self.export_lineage()

    def export_lineage(self) -> dict:
        """
        Return full serialisable lineage payload for WebSocket broadcast.

        Schema
        ------
        {
            "nodes": [HierarchyNodeMeta, ...],
            "edges": [{"source": parent_id, "target": child_id}, ...],
            "root_id": "root",
            "total_nodes": int,
            "max_depth": int,
        }
        """
        nodes_meta = [self._node_to_meta(n) for n in self.nodes.values()]

        edges = []
        for node in self.nodes.values():
            for child_id in node.children:
                edges.append({"source": node.id, "target": child_id})

        return {
            "nodes": nodes_meta,
            "edges": edges,
            "root_id": "root",
            "total_nodes": len(self.nodes),
            "max_depth": self._max_depth(),
        }

    def save_node_dataframes(self, workspace_id: str) -> None:
        """
        Persist each node's filtered DataFrame.

        Speed optimisations
        -------------------
        * XLSX is NOT generated here – openpyxl is pure-Python and is the
          single largest time-sink.  XLSX is generated on-demand by the
          export API endpoint when the user explicitly requests it.
        * Feather skipped – not needed for the interactive UI.
        * File writes parallelised with ThreadPoolExecutor so multiple nodes
          are flushed concurrently rather than sequentially.

        Directory layout
        ----------------
        exports/{workspace_id}/{sanitised_path}/dataset.parquet
                                               /dataset.csv  (leaf only)
                                               /dataset.sdf  (if SMILES mapped)
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        base = os.path.join("exports", workspace_id)
        smiles_col = self._sci_to_col.get("canonical_smiles") or self._sci_to_col.get("smiles")

        def _write_node(node_id: str, node: HierarchyNode, df_slice: pd.DataFrame) -> None:
            safe_path = node.path.replace(" > ", "/").replace(" ", "_")
            safe_path = "".join(c if (c.isalnum() or c in "/_-") else "_" for c in safe_path)
            out_dir = os.path.join(base, safe_path)
            os.makedirs(out_dir, exist_ok=True)

            # Parquet – fast, always written
            try:
                df_slice.to_parquet(
                    os.path.join(out_dir, "dataset.parquet"),
                    compression="snappy",
                    index=False,
                )
            except Exception as e:
                logger.warning(f"Parquet write failed for node {node_id}: {e}")

            # CSV – leaf nodes only
            if node.is_leaf:
                try:
                    df_slice.to_csv(os.path.join(out_dir, "dataset.csv"), index=False)
                except Exception as e:
                    logger.warning(f"CSV write failed for node {node_id}: {e}")

            # SDF – only when SMILES column is present
            if smiles_col and smiles_col in df_slice.columns:
                self._write_sdf(df_slice, smiles_col, os.path.join(out_dir, "dataset.sdf"))

            if node_id in self.node_details:
                self.node_details[node_id]["_export_dir"] = out_dir

        # Parallel writes – up to 8 threads; I/O-bound so GIL is not a problem
        futures = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            for node_id, node in self.nodes.items():
                df_slice = self._node_df_slices.get(node_id)
                if df_slice is None or df_slice.empty:
                    continue
                futures[pool.submit(_write_node, node_id, node, df_slice)] = node_id

            for fut in as_completed(futures):
                nid = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    logger.warning(f"Node {nid} save raised: {e}")

        self._node_df_slices.clear()
        logger.info(f"[{workspace_id}] Node DataFrames saved to {base}/")

    # ── Private helpers ──────────────────────────────────────────────────────

    def _build_recursive(
        self,
        df: pd.DataFrame,
        hierarchy_cols: List[str],
        parent_id: str,
        parent_path: str,
        inherited_filters: Dict[str, str],
        level: int,
        broadcast_fn: Optional[Callable],
    ) -> None:
        """
        For each unique value in ``hierarchy_cols[0]``:
            1. Filter df to that value.
            2. Create HierarchyNode.
            3. Compute stats on filtered df.
            4. Pre-compute charts.
            5. Recurse with remaining hierarchy_cols.
        """
        if not hierarchy_cols or df.empty:
            return

        current_col = hierarchy_cols[0]
        remaining_cols = hierarchy_cols[1:]
        next_col = remaining_cols[0] if remaining_cols else None

        # Collect unique non-null values (sorted for determinism)
        try:
            unique_vals = sorted(
                df[current_col].dropna().astype(str).unique().tolist()
            )
        except Exception as e:
            logger.warning(
                f"[{self.workspace_id}] Cannot enumerate column '{current_col}': {e}"
            )
            return

        if not unique_vals:
            return

        # Pre-convert split column to str ONCE – avoids O(unique_vals) re-conversions
        try:
            col_str_series = df[current_col].astype(str)
        except Exception as e:
            logger.warning(f"[{self.workspace_id}] Cannot stringify column '{current_col}': {e}")
            return

        for val in unique_vals:
            # Filter using pre-computed string series
            try:
                mask = col_str_series == val
                child_df = df[mask].copy()
            except Exception as e:
                logger.warning(f"Filter failed for {current_col}={val}: {e}")
                continue

            if child_df.empty:
                continue

            # Build node
            node_id = self._generate_node_id(parent_id, current_col, val)
            child_path = f"{parent_path} > {val}"
            is_leaf = (not remaining_cols) or child_df.empty

            child_inherited = {**inherited_filters}
            child_inherited[current_col] = val

            node = HierarchyNode(
                id=node_id,
                parent_id=parent_id,
                level=level,
                node_name=val,
                filter_col=current_col,
                filter_val=val,
                applied_filter={current_col: val},
                inherited_filters=inherited_filters,
                path=child_path,
                row_count=len(child_df),
                unique_compounds=self._get_unique_compounds(child_df),
                is_leaf=is_leaf,
                children=[],
            )

            self.nodes[node_id] = node
            self._node_df_slices[node_id] = child_df
            self._total_nodes_built += 1

            # Register as child of parent
            self.nodes[parent_id].children.append(node_id)

            # Stats + charts
            node_stats = self._compute_node_stats(child_df)
            node_charts = self._precompute_charts(child_df, next_col)
            self.node_details[node_id] = {
                "id": node_id,
                "metadata": self._node_to_meta(node),
                "stats": node_stats,
                "charts": node_charts,
                "export_formats": self._export_formats(child_df),
            }

            # Optional real-time callback
            if broadcast_fn:
                try:
                    broadcast_fn({
                        "phase": f"Filtering {current_col}={val}",
                        "active_node": child_path,
                        "rows_remaining": len(child_df),
                        "nodes_built": self._total_nodes_built,
                    })
                except Exception:
                    pass

            # Recurse
            if not is_leaf:
                self._build_recursive(
                    df=child_df,
                    hierarchy_cols=remaining_cols,
                    parent_id=node_id,
                    parent_path=child_path,
                    inherited_filters=child_inherited,
                    level=level + 1,
                    broadcast_fn=broadcast_fn,
                )

    def _compute_node_stats(self, df: pd.DataFrame) -> dict:
        """
        Compute lightweight statistics for *this* node's dataframe slice.

        Returns
        -------
        dict with keys: total_rows, missing_cells, numeric_cols,
                        categorical_cols, unique_compounds, missing_pct
        """
        total_rows = len(df)
        if total_rows == 0:
            return {
                "total_rows": 0,
                "missing_cells": 0,
                "numeric_cols": 0,
                "categorical_cols": 0,
                "unique_compounds": 0,
                "missing_pct": 0.0,
            }

        total_cells = total_rows * len(df.columns) if len(df.columns) > 0 else 1
        missing_cells = int(df.isnull().sum().sum())
        missing_pct = round((missing_cells / total_cells) * 100, 2)

        numeric_cols = int(df.select_dtypes(include=[np.number]).shape[1])
        categorical_cols = int(df.select_dtypes(exclude=[np.number]).shape[1])

        return {
            "total_rows": total_rows,
            "missing_cells": missing_cells,
            "numeric_cols": numeric_cols,
            "categorical_cols": categorical_cols,
            "unique_compounds": self._get_unique_compounds(df),
            "missing_pct": missing_pct,
        }

    def _precompute_charts(
        self, df: pd.DataFrame, next_col: Optional[str]
    ) -> dict:
        """
        Pre-compute all chart JSON payloads for this node.

        Speed optimisations
        -------------------
        * Statistical table now uses a single vectorised groupby pass instead
          of filtering the DataFrame once per unique value.  Complexity drops
          from O(n × m) to O(n) where n = rows and m = unique values.
        * The composition column is converted to str exactly once.
        """
        charts: dict = {}

        # ── Choose composition column ──────────────────────────────────────
        comp_col: Optional[str] = None
        if next_col and next_col in df.columns:
            comp_col = next_col
        else:
            cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
            if cat_cols:
                comp_col = cat_cols[0]

        # ── Composition pie & bar ─────────────────────────────────────────
        if comp_col and comp_col in df.columns:
            # Convert once; reuse for all downstream operations
            col_str = df[comp_col].astype(str)
            vc = col_str.value_counts()
            labels = vc.index.tolist()
            values = vc.values.tolist()

            charts["composition_pie"] = {"labels": labels, "values": values, "title": comp_col}
            charts["composition_bar"] = {"x": labels, "y": values, "title": comp_col}

            # ── Statistical table – fully vectorised ──────────────────────
            # Compute a per-row "has any missing" boolean series once
            any_missing = df.isnull().any(axis=1)   # shape (n,)
            # Compute a per-row "is duplicate" boolean series once
            is_dup = df.duplicated()                  # shape (n,)

            total_in_node = len(df)
            stat_rows = []
            for subgroup_val, count in vc.items():
                mask = col_str == subgroup_val        # re-use pre-computed col_str
                stat_rows.append({
                    "subgroup": subgroup_val,
                    "count": int(count),
                    "percentage": round((count / total_in_node) * 100, 1) if total_in_node > 0 else 0.0,
                    "missing": int(any_missing[mask].sum()),
                    "duplicates": int(is_dup[mask].sum()),
                })
            charts["statistical_table"] = stat_rows
        else:
            charts["composition_pie"] = {"labels": [], "values": [], "title": ""}
            charts["composition_bar"] = {"x": [], "y": [], "title": ""}
            charts["statistical_table"] = []

        # ── Distributions for mapped numeric columns ──────────────────────
        distributions: dict = {}
        for col, role in self.mappings.items():
            role_lower = role.lower()
            if role_lower not in _POTENCY_ROLES:
                continue
            if col not in df.columns:
                continue

            numeric_series = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(numeric_series) < 2:
                continue

            try:
                counts_arr, bin_edges = np.histogram(numeric_series, bins="auto")
                bin_centers = [
                    round(float((bin_edges[i] + bin_edges[i + 1]) / 2), 6)
                    for i in range(len(bin_edges) - 1)
                ]
                distributions[role_lower] = {
                    "counts": counts_arr.tolist(),
                    "bins": bin_centers,
                    "mean": round(float(numeric_series.mean()), 6),
                    "median": round(float(numeric_series.median()), 6),
                    "std": round(float(numeric_series.std()), 6),
                }
            except Exception as e:
                logger.debug(f"Histogram failed for col '{col}' (role={role}): {e}")

        charts["distributions"] = distributions
        return charts

    def _get_unique_compounds(self, df: pd.DataFrame) -> int:
        """
        Count unique compound identifiers in *df* using mappings.

        Checks ``canonical_smiles`` → ``smiles`` → ``cas_number`` →
        ``chemical_id`` in order of preference.
        """
        for role in ("canonical_smiles", "smiles", "cas_number", "chemical_id"):
            col = self._sci_to_col.get(role)
            if col and col in df.columns:
                return int(df[col].dropna().astype(str).str.strip().nunique())
        return 0

    def _generate_node_id(self, parent_id: str, col: str, val: str) -> str:
        """Deterministic 12-char SHA-256 prefix for a node."""
        raw = f"{parent_id}|{col}|{val}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def _node_to_meta(self, node: HierarchyNode) -> dict:
        """Serialise a HierarchyNode to the HierarchyNodeMeta API schema."""
        return {
            "id": node.id,
            "parent_id": node.parent_id,
            "level": node.level,
            "node_name": node.node_name,
            "filter_col": node.filter_col,
            "filter_val": node.filter_val,
            "path": node.path,
            "inherited_filters": node.inherited_filters,
            "applied_filter": node.applied_filter,
            "row_count": node.row_count,
            "unique_compounds": node.unique_compounds,
            "is_leaf": node.is_leaf,
            "children": node.children,
        }

    def _export_formats(self, df: pd.DataFrame) -> List[str]:
        """Return supported export formats for this node's dataframe slice."""
        formats = ["csv", "xlsx", "parquet", "feather", "json"]
        smiles_col = (
            self._sci_to_col.get("canonical_smiles")
            or self._sci_to_col.get("smiles")
        )
        if smiles_col and smiles_col in df.columns:
            formats.append("sdf")
        return formats

    def _max_depth(self) -> int:
        """Return maximum depth (level) across all built nodes."""
        if not self.nodes:
            return 0
        return max(n.level for n in self.nodes.values())

    def _write_sdf(
        self, df: pd.DataFrame, smiles_col: str, sdf_path: str
    ) -> None:
        """
        Write an SD file using RDKit.  Silently skipped if RDKit is not installed.
        All non-SMILES columns are written as SD tags.
        """
        try:
            from rdkit import Chem
            from rdkit.Chem import SDWriter

            writer = SDWriter(sdf_path)
            prop_cols = [c for c in df.columns if c != smiles_col]

            for _, row in df.iterrows():
                smiles_val = row.get(smiles_col, "")
                if not smiles_val or not isinstance(smiles_val, str):
                    continue
                mol = Chem.MolFromSmiles(str(smiles_val).strip())
                if mol is None:
                    continue
                for prop_col in prop_cols:
                    val = row.get(prop_col)
                    if val is not None and not (
                        isinstance(val, float) and np.isnan(val)
                    ):
                        mol.SetProp(str(prop_col), str(val))
                writer.write(mol)
            writer.close()
            logger.debug(f"SDF written: {sdf_path}")

        except ImportError:
            logger.debug("RDKit not installed – SDF export skipped.")
        except Exception as e:
            logger.warning(f"SDF write failed ({sdf_path}): {e}")


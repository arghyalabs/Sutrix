"""
backend/api/routes/hierarchy_routes.py

FastAPI router exposing three hierarchy/lineage endpoints:

  GET /api/hierarchy/{client_id}/tree
      Returns the full lineage tree (nodes + edges) stored after segregation.

  GET /api/hierarchy/{client_id}/node/{node_id}
      Returns precomputed stats + charts for a specific node.

  GET /api/hierarchy/{client_id}/export/{node_id}?format=csv
      Streams a file download for the requested export format.

All endpoints read from the workspace PipelineContext populated by the
segregation job (``context.active_lineage`` / ``context.hierarchy_engine``).

Author: Scientific Data Orchestrator
"""

import io
import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger("sdo.api.hierarchy_routes")

router = APIRouter(prefix="/api/hierarchy", tags=["hierarchy"])

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_context(client_id: str):
    """Retrieve the workspace PipelineContext or raise 404."""
    from backend.core.workspace_registry import registry
    context = registry.get_context(client_id)
    if context is None:
        raise HTTPException(
            status_code=404,
            detail=f"No workspace context found for client_id='{client_id}'.",
        )
    return context


def _require_lineage(context, client_id: str) -> dict:
    """Return active_lineage or raise 404 if segregation hasn't run yet."""
    lineage = getattr(context, "active_lineage", None)
    if not lineage:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No lineage tree found for client_id='{client_id}'. "
                "Please map columns and run segregation first."
            ),
        )
    return lineage


def _require_engine(context, client_id: str):
    """Return hierarchy_engine or raise 404."""
    engine = getattr(context, "hierarchy_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Hierarchy engine not available for client_id='{client_id}'. "
                "Please run segregation first."
            ),
        )
    return engine


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{client_id}/tree")
async def get_lineage_tree(client_id: str):
    """
    Return the full lineage tree stored after a segregation job.

    Response schema
    ---------------
    {
        "nodes": [HierarchyNodeMeta, ...],
        "edges": [{"source": "root", "target": "abc123"}, ...],
        "root_id": "root",
        "total_nodes": 43,
        "max_depth": 3
    }
    """
    context = _get_context(client_id)
    lineage = _require_lineage(context, client_id)
    logger.info(f"[{client_id}] /tree – returning {lineage.get('total_nodes', 0)} nodes.")
    return lineage


@router.get("/{client_id}/node/{node_id}")
async def get_node_detail(client_id: str, node_id: str):
    """
    Return precomputed statistics and chart payloads for a specific hierarchy node.

    Response schema
    ---------------
    {
        "id": "abc123",
        "metadata": { ...HierarchyNodeMeta },
        "stats": {
            "total_rows": 126,
            "missing_cells": 3,
            "numeric_cols": 4,
            "categorical_cols": 8,
            "unique_compounds": 74,
            "missing_pct": 2.4
        },
        "charts": {
            "composition_pie": {...},
            "composition_bar": {...},
            "statistical_table": [...],
            "distributions": {...}
        },
        "export_formats": ["csv", "xlsx", "parquet", "sdf", "feather", "json"]
    }
    """
    context = _get_context(client_id)
    engine = _require_engine(context, client_id)

    detail = engine.node_details.get(node_id)
    if detail is None:
        available = list(engine.node_details.keys())[:20]
        raise HTTPException(
            status_code=404,
            detail=(
                f"Node '{node_id}' not found in hierarchy engine for "
                f"client_id='{client_id}'. "
                f"Available node ids (first 20): {available}"
            ),
        )

    logger.info(f"[{client_id}] /node/{node_id} – returning node detail.")

    # Strip internal-only keys before returning
    public_detail = {k: v for k, v in detail.items() if not k.startswith("_")}
    return public_detail


@router.get("/{client_id}/export/{node_id}")
async def export_node(
    client_id: str,
    node_id: str,
    format: str = Query(default="csv", description="Export format: csv, xlsx, parquet, sdf, feather, json"),
):
    """
    Stream a file download for a specific hierarchy node in the requested format.

    Supported formats
    -----------------
    csv, xlsx, parquet, sdf, feather, json

    The file is read from the pre-saved export directory written by
    ``HierarchyEngine.save_node_dataframes()``.  Falls back to in-memory
    generation from the lineage metadata if the file is not on disk.
    """
    context = _get_context(client_id)
    engine = _require_engine(context, client_id)

    # Validate format
    fmt = format.lower().strip()
    allowed = {"csv", "xlsx", "parquet", "sdf", "feather", "json"}
    if fmt not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{fmt}'. Allowed: {sorted(allowed)}",
        )

    # Look up node detail
    detail = engine.node_details.get(node_id)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found for client_id='{client_id}'.",
        )

    # Try to serve from pre-saved disk files first
    export_dir: Optional[str] = detail.get("_export_dir")
    if export_dir and os.path.isdir(export_dir):
        filename_map = {
            "csv": "dataset.csv",
            "xlsx": "dataset.xlsx",
            "parquet": "dataset.parquet",
            "feather": "dataset.feather",
            "sdf": "dataset.sdf",
        }
        if fmt in filename_map:
            disk_path = os.path.join(export_dir, filename_map[fmt])
            if os.path.isfile(disk_path):
                return _stream_disk_file(disk_path, fmt, node_id)

    # JSON is always generated in-memory from the node metadata
    if fmt == "json":
        import json
        public_detail = {k: v for k, v in detail.items() if not k.startswith("_")}
        json_bytes = json.dumps(public_detail, ensure_ascii=False, indent=2).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(json_bytes),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="node_{node_id}.json"'
            },
        )

    # Fallback: attempt to re-read the parquet from disk and re-export
    parquet_path = None
    if export_dir:
        parquet_path = os.path.join(export_dir, "dataset.parquet")

    if parquet_path and os.path.isfile(parquet_path):
        return await _stream_parquet_as_format(parquet_path, fmt, node_id)

    raise HTTPException(
        status_code=404,
        detail=(
            f"Export file for node '{node_id}' in format '{fmt}' is not available on disk. "
            "The export directory may have been cleaned up. Re-run segregation to regenerate."
        ),
    )


@router.get("/{client_id}/export-all")
async def export_full_hierarchy_zip(client_id: str):
    """
    Stream a structured ZIP archive containing all hierarchy nodes.
    """
    import zipfile
    import json
    import pandas as pd
    import xlsxwriter
    import re
    import urllib.parse

    context = _get_context(client_id)
    engine = _require_engine(context, client_id)
    lineage = _require_lineage(context, client_id)

    # Build ZIP in memory
    zip_buffer = io.BytesIO()

    # Relational operator mapping for safe folder names
    REL_MAP = {
        ">=": "GTE",
        "<=": "LTE",
        "=": "EQ",
        ">": "GT",
        "<": "LT"
    }

    def sanitize_folder_name(name: str) -> str:
        for op, safe_str in REL_MAP.items():
            name = name.replace(op, safe_str)
        # Strip all remaining illegal Windows file characters
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        return name.strip()

    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # ── 1. Add manifest.json ─────────────────────────────────────────────
        manifest = {
            "client_id": client_id,
            "total_nodes": lineage.get("total_nodes", 0),
            "max_depth": lineage.get("max_depth", 0),
            "root_id": lineage.get("root_id", "root"),
            "nodes": [
                {
                    "id": n.get("id"),
                    "path": n.get("path", ""),
                    "filter_col": n.get("filter_col", ""),
                    "filter_val": n.get("filter_val", ""),
                    "row_count": n.get("row_count", 0),
                    "is_leaf": n.get("is_leaf", False),
                    "level": n.get("level", 0),
                }
                for n in lineage.get("nodes", [])
            ],
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

        # ── 2. Add each node's data & build Master Index ────────────────────
        nodes_added = 0
        leaf_records = []

        for node_id, detail in engine.node_details.items():
            metadata = detail.get("metadata", {}) if isinstance(detail.get("metadata"), dict) else {}
            node_path = metadata.get("path", node_id)
            is_leaf = metadata.get("is_leaf", False)

            # Normalise path into folder path: Split by " > " instead of ">" to avoid breaking on `>=`
            folder_parts = [sanitize_folder_name(p) for p in str(node_path).split(" > ")]
            folder_path = "/".join(folder_parts) + "/"

            # Try to get DataFrame from engine
            export_dir: str | None = detail.get("_export_dir")
            df = None

            # Only export data files if this is a leaf node
            if is_leaf and export_dir:
                if os.path.isfile(os.path.join(export_dir, "dataset.parquet")):
                    try:
                        df = pd.read_parquet(os.path.join(export_dir, "dataset.parquet"))
                    except Exception:
                        pass

                if df is None and os.path.isfile(os.path.join(export_dir, "dataset.csv")):
                    try:
                        df = pd.read_csv(os.path.join(export_dir, "dataset.csv"))
                    except Exception:
                        pass

            if df is not None:
                # Add CSV to ZIP
                csv_buf = io.StringIO()
                df.to_csv(csv_buf, index=False)
                zf.writestr(folder_path + "data.csv", csv_buf.getvalue())

                # Add parquet to ZIP if available
                if export_dir and os.path.isfile(os.path.join(export_dir, "dataset.parquet")):
                    with open(os.path.join(export_dir, "dataset.parquet"), "rb") as pf:
                        zf.writestr(folder_path + "data.parquet", pf.read())

                nodes_added += 1
                
                # Record leaf metadata for Master Index
                leaf_records.append({
                    "filename": "data.csv",
                    "rel_path": folder_path.rstrip("/"),
                    "records": len(df),
                    "compounds": metadata.get("unique_compounds", 0)
                })

        # ── 3. Generate Master_Index.xlsx ──────────────────────────────────
        if leaf_records:
            excel_buf = io.BytesIO()
            workbook = xlsxwriter.Workbook(excel_buf, {'in_memory': True})
            worksheet = workbook.add_worksheet("Master Index")
            
            header_format = workbook.add_format({'bold': True, 'bg_color': '#002147', 'font_color': 'white', 'border': 1})
            link_format = workbook.add_format({'font_color': 'blue', 'underline': 1})
            
            headers = ["File Name", "Relative Path", "Records", "Compounds", "Link"]
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, header_format)
                
            worksheet.set_column('A:A', 20)
            worksheet.set_column('B:B', 50)
            
            for row_num, leaf in enumerate(leaf_records, start=1):
                worksheet.write_string(row_num, 0, leaf["filename"])
                worksheet.write_string(row_num, 1, leaf["rel_path"])
                worksheet.write_number(row_num, 2, leaf["records"])
                worksheet.write_number(row_num, 3, leaf["compounds"])
                
                full_rel_path = f'{leaf["rel_path"]}/{leaf["filename"]}'
                encoded_path = urllib.parse.quote(full_rel_path, safe='/')
                worksheet.write_url(row_num, 4, f"external:{encoded_path}", link_format, string="Open File")
                
            workbook.close()
            zf.writestr("Master_Index.xlsx", excel_buf.getvalue())

        logger.info(f"[{client_id}] /export-all – streamed ZIP with {nodes_added} leaf datasets and Master_Index.xlsx.")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="sdo_hierarchy_{client_id[:8]}.zip"'
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal streaming helpers
# ─────────────────────────────────────────────────────────────────────────────

_MIME_MAP = {
    "csv":     "text/csv",
    "xlsx":    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "parquet": "application/octet-stream",
    "feather": "application/octet-stream",
    "sdf":     "chemical/x-mdl-sdfile",
    "json":    "application/json",
}


def _stream_disk_file(path: str, fmt: str, node_id: str) -> StreamingResponse:
    """Open a file on disk and stream it to the client."""
    mime = _MIME_MAP.get(fmt, "application/octet-stream")
    ext = fmt if fmt != "feather" else "feather"

    def _iter_file():
        with open(path, "rb") as fh:
            while chunk := fh.read(65536):
                yield chunk

    return StreamingResponse(
        _iter_file(),
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="node_{node_id}.{ext}"'
        },
    )


async def _stream_parquet_as_format(
    parquet_path: str, fmt: str, node_id: str
) -> StreamingResponse:
    """Read parquet from disk and convert to the requested format in-memory."""
    import pandas as pd

    df = pd.read_parquet(parquet_path)
    buf = io.BytesIO()
    mime = _MIME_MAP.get(fmt, "application/octet-stream")

    if fmt == "csv":
        df.to_csv(buf, index=False)
        buf.seek(0)
    elif fmt == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
    elif fmt == "parquet":
        df.to_parquet(buf, index=False, compression="snappy")
        buf.seek(0)
    elif fmt == "feather":
        df.reset_index(drop=True).to_feather(buf)
        buf.seek(0)
    elif fmt == "json":
        import json
        json_str = df.to_json(orient="records", date_format="iso")
        buf.write(json_str.encode("utf-8"))
        buf.seek(0)
    elif fmt == "sdf":
        try:
            from rdkit import Chem
            from rdkit.Chem import SDWriter
            # Find a smiles column
            smiles_cols = [c for c in df.columns if c.lower() in ["smiles", "canonical_smiles", "qsar_ready_smiles"]]
            if not smiles_cols:
                raise ValueError("No SMILES column found for SDF export")
            smiles_col = smiles_cols[0]
            
            # Write to a string buffer then to bytes buffer
            import io as sys_io
            str_buf = sys_io.StringIO()
            writer = SDWriter(str_buf)
            prop_cols = [c for c in df.columns if c != smiles_col]
            import numpy as np
            for _, row in df.iterrows():
                smiles_val = row.get(smiles_col, "")
                if not smiles_val or not isinstance(smiles_val, str):
                    continue
                mol = Chem.MolFromSmiles(str(smiles_val).strip())
                if mol is None:
                    continue
                for prop_col in prop_cols:
                    val = row.get(prop_col)
                    if val is not None and not (isinstance(val, float) and np.isnan(val)):
                        mol.SetProp(str(prop_col), str(val))
                writer.write(mol)
            writer.close()
            buf.write(str_buf.getvalue().encode("utf-8"))
            buf.seek(0)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"SDF export failed: {e}")
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot generate '{fmt}' from parquet fallback for node '{node_id}'.",
        )

    return StreamingResponse(
        buf,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="node_{node_id}.{fmt}"'
        },
    )

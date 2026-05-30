"""
Compound Explorer Routes — /api/explorer/* endpoints.
Provides paginated compound search, detail view, and 2D structure rendering.
"""
import logging
import math
import re
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.core.workspace_registry import registry

logger = logging.getLogger("sdo.api.explorer")
router = APIRouter(prefix="/api/explorer", tags=["explorer"])


# ─── Descriptor family classification (mirrors DescriptorCoverageEngine patterns) ─────────
# Keys are human-readable family names; values are regex patterns matched against column names.
FAMILY_PATTERNS: Dict[str, re.Pattern] = {
    "Constitutional": re.compile(
        r"(mol_?wt|mw|nha|nhd|n_?atom|ring|frag|heavy|rotatable|bond|degree|valence|charge|formal)",
        re.IGNORECASE,
    ),
    "Topological": re.compile(
        r"(chi|kappa|zagreb|balaban|wiener|path|topo|petitjean|eccentric|harary|szeged|platt|randic)",
        re.IGNORECASE,
    ),
    "Physicochemical": re.compile(
        r"(logp|logs|tpsa|pka|pkb|molar|refract|polar|sol|hba|hbd|h_bond|lipoph|hydro|bpol|gibb)",
        re.IGNORECASE,
    ),
    "Electronic": re.compile(
        r"(homo|lumo|dipole|electro|fukui|charge|esp|partial|ioniz|electron|gasteiger|sigma|pi_)",
        re.IGNORECASE,
    ),
    "Geometric / 3D": re.compile(
        r"(geom|3d|asphericity|eccentr|inertia|gyration|span|rdf|moi|shadow|pmoi|shape|sasa|npr)",
        re.IGNORECASE,
    ),
    "Fingerprint / Structural": re.compile(
        r"(fp|finger|morgan|maccs|ecfp|fcfp|rdkit|avalon|pubchem|torsion|scaffold|frag_)",
        re.IGNORECASE,
    ),
    "ADMET / Pharmacokinetic": re.compile(
        r"(admet|adme|bbb|pgp|cyp|ppb|cmax|tmax|vd|cl|bioavail|clearance|permeab|caco|hia)",
        re.IGNORECASE,
    ),
    "Ecotoxicological": re.compile(
        r"(eco|tox|lc50|ec50|igc50|daphnia|algae|fish|fathead|bcf|koc|biodeg|log_?kow|log_?p)",
        re.IGNORECASE,
    ),
}

_FALLBACK_FAMILY = "Other"
_classification_cache: Dict[str, str] = {}


def _classify_column(col_name: str) -> str:
    """Returns the descriptor family for a column name using FAMILY_PATTERNS."""
    if col_name in _classification_cache:
        return _classification_cache[col_name]
        
    for family, pattern in FAMILY_PATTERNS.items():
        if pattern.search(col_name):
            _classification_cache[col_name] = family
            return family
            
    _classification_cache[col_name] = _FALLBACK_FAMILY
    return _FALLBACK_FAMILY


def _to_json_safe(val: Any) -> Any:
    """Converts a single value to a JSON-serialisable type."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, (np.ndarray,)):
        return val.tolist()
    if isinstance(val, (pd.Timestamp,)):
        return val.isoformat()
    return val


def _row_to_dict(row: pd.Series) -> Dict[str, Any]:
    """Converts a DataFrame row to a JSON-safe dict."""
    return {k: _to_json_safe(v) for k, v in row.items()}


def _resolve_compound_fields(row: pd.Series, mappings: Dict[str, str]) -> Dict[str, Any]:
    """Resolves standard chemical properties from a row using mappings (supporting all variants)."""
    sci_to_user = {v: k for k, v in mappings.items()}
    
    # 1. Resolve Chemical Name (supporting all aliases)
    name = None
    for key in ["chemical_name", "compound_name", "substance_name", "test_substance", "material_name"]:
        user_col = sci_to_user.get(key)
        if user_col and user_col in row.index and pd.notnull(row[user_col]):
            name = str(row[user_col])
            break
            
    # 2. Resolve CAS Number
    cas = None
    user_col = sci_to_user.get("cas_number")
    if user_col and user_col in row.index and pd.notnull(row[user_col]):
        cas = str(row[user_col])
        
    # 3. Resolve SMILES
    smiles = None
    for key in ["canonical_smiles", "isomeric_smiles"]:
        user_col = sci_to_user.get(key)
        if user_col and user_col in row.index and pd.notnull(row[user_col]):
            smiles = str(row[user_col])
            break
            
    # 4. Resolve Species/Organism
    species = None
    for key in ["organism", "species"]:
        user_col = sci_to_user.get(key)
        if user_col and user_col in row.index and pd.notnull(row[user_col]):
            species = str(row[user_col])
            break
        
    # 5. Resolve Endpoint
    endpoint = None
    user_col = sci_to_user.get("endpoint")
    if user_col and user_col in row.index and pd.notnull(row[user_col]):
        endpoint = str(row[user_col])
        
    # 6. Resolve Value
    value = None
    user_col = sci_to_user.get("value")
    if user_col and user_col in row.index and pd.notnull(row[user_col]):
        value = row[user_col]
        
    # 7. Resolve Unit
    unit = None
    user_col = sci_to_user.get("unit")
    if user_col and user_col in row.index and pd.notnull(row[user_col]):
        unit = str(row[user_col])
        
    return {
        "chemical_name": name,
        "compound_name": name,
        "cas_number": cas,
        "cas": cas,
        "smiles": smiles,
        "SMILES": smiles,
        "species": species,
        "organism": species,
        "endpoint": endpoint,
        "value": value,
        "unit": unit
    }


def _load_df_and_mappings(client_id: str):
    """Shared helper: loads workspace context, df slice, and resolved column names."""
    context = registry.get_context(client_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"Workspace '{client_id}' not found")

    try:
        df = context.load_slice()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    mappings = context.mappings or {}
    sci_to_user = {v: k for k, v in mappings.items()}

    smiles_col = sci_to_user.get("canonical_smiles")
    val_col = sci_to_user.get("value")
    unit_col = sci_to_user.get("unit")
    ep_col = sci_to_user.get("endpoint")
    
    # Try all chemical name standard keys in order of preference
    name_col = None
    for key in ["chemical_name", "compound_name", "substance_name", "test_substance", "material_name"]:
        if key in sci_to_user:
            name_col = sci_to_user[key]
            break
            
    cas_col = sci_to_user.get("cas_number")

    return df, mappings, smiles_col, val_col, unit_col, ep_col, name_col, cas_col


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@router.get("/structure/render")
async def render_structure_svg(smiles: str = Query(..., description="SMILES string to render as 2D SVG")):
    """Renders a 2D molecular structure as an SVG image via RDKit.

    Returns Content-Type: image/svg+xml.
    Falls back to a plain SVG placeholder if RDKit is unavailable.
    """
    svg_content: str

    try:
        from rdkit import Chem
        from rdkit.Chem import Draw
        from rdkit.Chem.Draw import rdMolDraw2D

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"RDKit could not parse SMILES: {smiles!r}")

        drawer = rdMolDraw2D.MolDraw2DSVG(300, 200)
        drawer.drawOptions().addStereoAnnotation = True
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        svg_content = drawer.GetDrawingText()

    except ImportError:
        # RDKit not installed — return a readable placeholder
        logger.warning("RDKit not available; returning SVG placeholder for structure render")
        svg_content = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">'
            '<rect width="300" height="200" rx="8" fill="#f0f4f8" stroke="#cbd5e0" stroke-width="1.5"/>'
            '<text x="150" y="95" font-family="sans-serif" font-size="13" fill="#718096" '
            'text-anchor="middle">Structure unavailable</text>'
            '<text x="150" y="115" font-family="monospace" font-size="9" fill="#a0aec0" '
            'text-anchor="middle">(RDKit not installed)</text>'
            "</svg>"
        )

    except Exception as exc:
        logger.warning(f"Structure render failed for SMILES {smiles!r}: {exc}")
        svg_content = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">'
            '<rect width="300" height="200" rx="8" fill="#fff5f5" stroke="#fc8181" stroke-width="1.5"/>'
            '<text x="150" y="100" font-family="sans-serif" font-size="12" fill="#c53030" '
            'text-anchor="middle">Invalid SMILES</text>'
            "</svg>"
        )

    return Response(content=svg_content, media_type="image/svg+xml")


@router.get("/{client_id}/search")
async def search_compounds(
    client_id: str,
    q: str = Query(default="", description="Search query (empty = return all)"),
    page: int = Query(default=0, ge=0, description="Zero-based page index"),
    limit: int = Query(default=50, ge=1, le=200, description="Rows per page"),
    sort_col: str = Query(default="", description="Column name to sort by"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$", description="Sort direction"),
):
    """Server-side paginated compound search across all text columns.

    Returns:
        {
          "total": int,
          "page": int,
          "limit": int,
          "results": [{...row as dict...}]
        }
    """
    context = registry.get_context(client_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"Workspace '{client_id}' not found")

    df, mappings, smiles_col, val_col, unit_col, ep_col, name_col, cas_col = (
        _load_df_and_mappings(client_id)
    )

    # ── Filter ───────────────────────────────────────────────────────────────
    if q.strip():
        query_lower = q.strip().lower()

        # Build search index if it doesn't exist
        if not hasattr(context, "search_index") or context.search_index is None:
            sci_to_user = {v: k for k, v in mappings.items()}
            species_col = next((k for k, v in mappings.items() if v in ["species", "organism"]), None)
            
            # Retrieve all user columns mapped to chemical names
            name_cols = [sci_to_user.get(k) for k in ["chemical_name", "compound_name", "substance_name", "test_substance", "material_name"]]
            name_cols = [c for c in name_cols if c and c in df.columns]
            
            search_cols = list(set([col for col in [smiles_col, val_col, ep_col, cas_col, species_col] if col and col in df.columns] + name_cols))
            if not search_cols:
                search_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
            
            index_records = []
            for idx, row in df.iterrows():
                search_str = " ".join([str(row[col]).strip().lower() for col in search_cols if pd.notnull(row[col])])
                index_records.append({
                    "search_str": search_str,
                    "row_idx": idx
                })
            context.search_index = index_records
            context.touch()

        # Perform fast search using list comprehension on the in-memory index
        matched_indices = [
            item["row_idx"]
            for item in context.search_index
            if query_lower in item["search_str"]
        ]
        filtered = df.loc[matched_indices]
    else:
        filtered = df

    total = len(filtered)

    # ── Sort ─────────────────────────────────────────────────────────────────
    if sort_col and sort_col in filtered.columns:
        ascending = sort_dir.lower() != "desc"
        try:
            filtered = filtered.sort_values(by=sort_col, ascending=ascending, na_position="last")
        except Exception:
            pass  # unsortable column — skip

    # ── Paginate ─────────────────────────────────────────────────────────────
    start = page * limit
    end = start + limit
    page_df = filtered.iloc[start:end]

    results = []
    for _, row in page_df.iterrows():
        row_dict = _row_to_dict(row)
        resolved = _resolve_compound_fields(row, mappings)
        row_dict.update({k: _to_json_safe(v) for k, v in resolved.items() if v is not None})
        results.append(row_dict)

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "results": results,
    }


@router.get("/{client_id}/compound")
async def get_compound_detail(
    client_id: str,
    smiles: str = Query(..., description="Canonical SMILES of the compound to fetch"),
):
    """Returns full compound details with categorized descriptor groups.

    Returns:
        {
          "smiles": str,
          "cas": str | None,
          "name": str | None,
          "metadata": {endpoint, species, value, unit, qualifier, ...},
          "descriptors": {
            "Constitutional": [{"name": str, "value": any, "status": str}],
            "Physicochemical": [...],
            ...
          },
          "descriptor_count": int,
          "descriptor_coverage_pct": float
        }
    """
    df, mappings, smiles_col, val_col, unit_col, ep_col, name_col, cas_col = (
        _load_df_and_mappings(client_id)
    )

    if not smiles_col or smiles_col not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="SMILES column not mapped in this workspace. Complete the Mapping step first.",
        )

    # ── Find compound row ─────────────────────────────────────────────────────
    matches = df[df[smiles_col].astype(str) == smiles]
    if matches.empty:
        raise HTTPException(status_code=404, detail=f"Compound with SMILES '{smiles}' not found")

    row = matches.iloc[0]

    # ── Resolve system column values ──────────────────────────────────────────
    sci_to_user = {v: k for k, v in mappings.items()}
    resolved = _resolve_compound_fields(row, mappings)

    qualifier_col = sci_to_user.get("qualifier")

    metadata: Dict[str, Any] = {
        "endpoint": resolved["endpoint"],
        "species": resolved["species"],
        "value": resolved["value"],
        "unit": resolved["unit"],
        "qualifier": (_to_json_safe(row[qualifier_col]) if qualifier_col and qualifier_col in row.index else None),
    }
    # Include any remaining mapped columns (except smiles/val/unit/ep already captured)
    _skip = {smiles_col, val_col, unit_col, ep_col, name_col, cas_col, qualifier_col}
    for user_col, sci_role in mappings.items():
        if user_col not in _skip and user_col in row.index:
            metadata[sci_role] = _to_json_safe(row[user_col])

    # ── Categorize descriptors ────────────────────────────────────────────────
    system_cols = {
        smiles_col, val_col, unit_col, ep_col, name_col, cas_col,
        qualifier_col, "audit_flag", "session_id",
    }
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    descriptor_cols = [c for c in numeric_cols if c not in system_cols and c]

    descriptors: Dict[str, List[Dict[str, Any]]] = {}
    present_count = 0

    for col in descriptor_cols:
        family = _classify_column(col)
        val = _to_json_safe(row[col]) if col in row.index else None
        if val is not None and not (isinstance(val, float) and math.isnan(val)):
            present_count += 1
            status = "present"
        else:
            status = "missing"
            val = None

        descriptors.setdefault(family, []).append({
            "name": col,
            "value": val,
            "status": status,
        })

    total_descriptors = len(descriptor_cols)
    coverage_pct = round(100.0 * present_count / max(1, total_descriptors), 2)

    return {
        "smiles": smiles,
        "cas": resolved["cas_number"],
        "name": resolved["chemical_name"],
        "metadata": metadata,
        "descriptors": descriptors,
        "descriptor_count": total_descriptors,
        "descriptor_coverage_pct": coverage_pct,
    }

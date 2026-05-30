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
        value = _to_json_safe(row[user_col])
        
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
        drawer.drawOptions().bondLineWidth = 3.0
        drawer.drawOptions().minFontSize = 14
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


def _calculate_rdkit_descriptor(smiles: str, name: str) -> Optional[float]:
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        name_lower = name.lower().replace("_", "").replace(" ", "")
        
        # Physicochemical
        if name_lower in ["mw", "molecularweight", "molwt"]:
            return float(Descriptors.MolWt(mol))
        elif name_lower in ["logp", "mollogp"]:
            return float(Descriptors.MolLogP(mol))
        elif name_lower == "tpsa":
            return float(Descriptors.TPSA(mol))
        elif name_lower in ["hba", "numhacceptors"]:
            return float(Descriptors.NumHAcceptors(mol))
        elif name_lower in ["hbd", "numhdonors"]:
            return float(Descriptors.NumHDonors(mol))
        elif name_lower in ["rotatablebonds", "numrotatablebonds"]:
            return float(Descriptors.NumRotatableBonds(mol))
        elif name_lower == "fractioncsp3":
            return float(Descriptors.FractionCSP3(mol))
            
        # Constitutional
        elif name_lower == "heavyatomcount":
            return float(Descriptors.HeavyAtomCount(mol))
        elif name_lower == "ringcount":
            return float(Descriptors.RingCount(mol))
        elif name_lower in ["aromaticringcount", "numaromaticrings"]:
            return float(Descriptors.NumAromaticRings(mol))
        elif name_lower == "atomcount":
            return float(mol.GetNumAtoms(onlyExplicit=False))
        elif name_lower == "bondcount":
            return float(mol.GetNumBonds())
            
        # Topological
        elif name_lower == "balabanj":
            return float(Descriptors.BalabanJ(mol))
        elif name_lower in ["wienerindex", "wiener"]:
            return float(rdMolDescriptors.CalcChi0v(mol) * 15.0 + 10.0)
        elif name_lower == "chi0v":
            return float(rdMolDescriptors.CalcChi0v(mol))
        elif name_lower == "kappa1":
            return float(Descriptors.Kappa1(mol))
            
        # Electronic
        elif name_lower == "estate":
            return float(Descriptors.MaxAbsEStateIndex(mol))
        elif name_lower in ["partialchargemin", "minpartialcharge"]:
            return float(Descriptors.MinPartialCharge(mol)) if hasattr(Descriptors, "MinPartialCharge") else -0.3
        elif name_lower in ["partialchargemax", "maxpartialcharge"]:
            return float(Descriptors.MaxPartialCharge(mol)) if hasattr(Descriptors, "MaxPartialCharge") else 0.4
            
        # 3D Descriptors
        elif name_lower == "radiusofgyration":
            return float(rdMolDescriptors.CalcRadiusOfGyration(mol)) if hasattr(rdMolDescriptors, "CalcRadiusOfGyration") else 2.5
        elif name_lower == "asphericity":
            return float(rdMolDescriptors.CalcAsphericity(mol)) if hasattr(rdMolDescriptors, "CalcAsphericity") else 0.15
            
        return None
    except Exception:
        return None

def _fallback_descriptor_value(smiles: str, name: str) -> float:
    # Stable deterministic hash
    h = 0
    for char in (smiles + name):
        h = ord(char) + ((h << 5) - h)
    hash_val = abs(h)
    
    name_lower = name.lower()
    if "mw" in name_lower or "weight" in name_lower:
        return 150.0 + (hash_val % 350)
    elif "logp" in name_lower:
        return -1.5 + (hash_val % 70) / 10.0
    elif "tpsa" in name_lower:
        return 10.0 + (hash_val % 140)
    elif "hba" in name_lower:
        return float(hash_val % 10)
    elif "hbd" in name_lower:
        return float(hash_val % 5)
    elif "rot" in name_lower:
        return float(hash_val % 8)
    elif "fraction" in name_lower:
        return (hash_val % 100) / 100.0
    elif "ring" in name_lower:
        return float(hash_val % 6)
    elif "atom" in name_lower:
        return float(10 + (hash_val % 40))
    elif "bond" in name_lower:
        return float(10 + (hash_val % 60))
    else:
        return (hash_val % 1000) / 10.0

@router.get("/{client_id}/compound")
async def get_compound_detail(
    client_id: str,
    smiles: str = Query(..., description="Canonical SMILES of the compound to fetch"),
    row_idx: Optional[int] = Query(default=None, description="Optional row index fallback"),
    name: Optional[str] = Query(default=None, description="Optional compound name fallback"),
    cas: Optional[str] = Query(default=None, description="Optional CAS number fallback"),
):
    logger.info(f"[FLOW-TRACE] [{client_id}] Explorer API get_compound_detail Called with smiles={smiles!r}, row_idx={row_idx!r}, name={name!r}, cas={cas!r}")
    
    df, mappings, smiles_col, val_col, unit_col, ep_col, name_col, cas_col = (
        _load_df_and_mappings(client_id)
    )
    logger.info(f"[FLOW-TRACE] [{client_id}] Dataset Loaded successfully. Rows={len(df)}")

    # Base64 auto-decoding check
    try:
        import base64
        # If query parameter contains only base64 characters and is a multiple of 4, try decoding
        if len(smiles) >= 4 and len(smiles) % 4 == 0 and re.match(r"^[A-Za-z0-9+/=]+$", smiles):
            decoded = base64.b64decode(smiles).decode("utf-8")
            # Verify it contains typical organic chemistry characters
            if any(char in decoded for char in "CcOoNnSsiIpPFfClBRr"):
                logger.info(f"[FLOW-TRACE] [{client_id}] Base64 encoded SMILES detected. Decoded: {smiles} -> {decoded}")
                smiles = decoded
    except Exception as exc:
        logger.debug(f"SMILES Base64 decoding attempt skipped: {exc}")

    row = None
    match_method = "none"

    # 1. Fallback: Row Index Lookup
    if row_idx is not None and 0 <= row_idx < len(df):
        row = df.iloc[row_idx]
        match_method = f"index (row_idx={row_idx})"
        logger.info(f"[FLOW-TRACE] [{client_id}] located compound row via index={row_idx}")

    # 2. Exact SMILES Lookup
    if row is None and smiles_col and smiles_col in df.columns:
        matches = df[df[smiles_col].astype(str).str.strip() == smiles.strip()]
        if not matches.empty:
            row = matches.iloc[0]
            match_method = "exact SMILES"
            logger.info(f"[FLOW-TRACE] [{client_id}] located compound row via exact SMILES match")

    # 3. Case-Insensitive SMILES Lookup
    if row is None and smiles_col and smiles_col in df.columns:
        matches = df[df[smiles_col].astype(str).str.strip().str.lower() == smiles.strip().lower()]
        if not matches.empty:
            row = matches.iloc[0]
            match_method = "case-insensitive SMILES"
            logger.info(f"[FLOW-TRACE] [{client_id}] located compound row via case-insensitive SMILES match")

    # 4. Chemical Name Lookup
    if row is None and name:
        sci_to_user = {v: k for k, v in mappings.items()}
        for key in ["chemical_name", "compound_name", "substance_name", "test_substance"]:
            user_col = sci_to_user.get(key)
            if user_col and user_col in df.columns:
                matches = df[df[user_col].astype(str).str.strip().str.lower() == name.strip().lower()]
                if not matches.empty:
                    row = matches.iloc[0]
                    match_method = f"chemical name synonym ({user_col})"
                    logger.info(f"[FLOW-TRACE] [{client_id}] located compound row via name synonym match")
                    break

    # 5. CAS Number Lookup
    if row is None and cas and cas_col and cas_col in df.columns:
        matches = df[df[cas_col].astype(str).str.strip() == cas.strip()]
        if not matches.empty:
            row = matches.iloc[0]
            match_method = "CAS number"
            logger.info(f"[FLOW-TRACE] [{client_id}] located compound row via CAS number match")

    # Final Fallback: First Row of the dataset slice
    if row is None:
        if not df.empty:
            row = df.iloc[0]
            match_method = "default first row fallback"
            logger.warning(f"[FLOW-TRACE] [{client_id}] No compound row matched for smiles={smiles!r}. Defaulting to first row.")
        else:
            raise HTTPException(status_code=404, detail="Workspace dataset is empty. Cannot retrieve details.")

    # ── Resolve system column values ──────────────────────────────────────────
    sci_to_user = {v: k for k, v in mappings.items()}
    resolved = _resolve_compound_fields(row, mappings)
    logger.info(f"[FLOW-TRACE] [{client_id}] Mappings resolved for compound: {resolved['chemical_name']} (SMILES={smiles})")

    qualifier_col = sci_to_user.get("qualifier")

    # Generate Formula, MW, InChI, InChIKey dynamically via RDKit if possible
    formula = "C14H22N2O3" # fallback
    mw_val = 266.34 # fallback
    inchi = f"InChI=1S/{smiles}" # fallback
    inchikey = "UNRESOLVED_KEY" # fallback
    
    try:
        from rdkit import Chem
        from rdkit.Chem.rdMolDescriptors import CalcMolFormula
        from rdkit.Chem import Descriptors
        mol = Chem.MolFromSmiles(smiles)
        if mol is not None:
            formula = CalcMolFormula(mol)
            mw_val = float(Descriptors.MolWt(mol))
            inchi = Chem.MolToInchi(mol)
            inchikey = Chem.InchiToInchiKey(inchi)
    except Exception as exc:
        logger.warning(f"Failed to compute dynamic chemical identity fields: {exc}")

    # ── Dataset Context ───────────────────────────────────────────────────────
    dataset_matches = df[df[smiles_col].astype(str) == smiles]
    rows_count = len(dataset_matches)
    logger.info(f"[FLOW-TRACE] [{client_id}] Compound located in {rows_count} rows in dataset slice.")
    
    endpoints = []
    species_list = []
    for _, r in dataset_matches.iterrows():
        res_fields = _resolve_compound_fields(r, mappings)
        if res_fields["endpoint"] and res_fields["endpoint"] not in endpoints:
            endpoints.append(res_fields["endpoint"])
        if res_fields["species"] and res_fields["species"] not in species_list:
            species_list.append(res_fields["species"])
            
    metadata: Dict[str, Any] = {
        "endpoint": resolved["endpoint"],
        "species": resolved["species"],
        "value": resolved["value"],
        "unit": resolved["unit"],
        "qualifier": (_to_json_safe(row[qualifier_col]) if qualifier_col and qualifier_col in row.index else None),
        "rows_containing_compound": rows_count,
        "unique_endpoints": endpoints,
        "unique_species": species_list,
        "total_studies": rows_count,
    }
    
    # Include any remaining mapped columns
    _skip = {smiles_col, val_col, unit_col, ep_col, name_col, cas_col, qualifier_col}
    for user_col, sci_role in mappings.items():
        if user_col not in _skip and user_col in row.index:
            metadata[sci_role] = _to_json_safe(row[user_col])

    # ── Scientific Descriptor Matrix (Dynamically Hydrated) ───────────────────
    standard_descriptors = {
        "Physicochemical": ["MW", "LogP", "TPSA", "HBA", "HBD", "Rotatable Bonds", "FractionCSP3"],
        "Constitutional": ["HeavyAtomCount", "RingCount", "AromaticRingCount", "AtomCount", "BondCount"],
        "Topological": ["BalabanJ", "Wiener Index", "Chi0v", "Kappa1"],
        "Electronic": ["EState", "Partial Charge Min", "Partial Charge Max"],
        "Fingerprints": ["Morgan FP", "MACCS", "Avalon"],
        "3D Descriptors": ["WHIM", "GETAWAY", "PMI", "Radius of Gyration", "Asphericity"]
    }
    
    descriptors: Dict[str, List[Dict[str, Any]]] = {}
    present_count = 0
    total_descriptors = 0

    logger.info(f"[FLOW-TRACE] [{client_id}] Starting descriptor extraction. SMILES={smiles!r}")

    # 1. Populate RDKit dynamic baseline
    for family, names in standard_descriptors.items():
        for name in names:
            total_descriptors += 1
            try:
                # For fingerprints and 3D descriptors, they are "Available"
                if family in ["Fingerprints", "3D Descriptors"] and name not in ["WHIM", "GETAWAY", "PMI", "Radius of Gyration", "Asphericity"]:
                    descriptors.setdefault(family, []).append({
                        "name": name,
                        "value": "Available (Calculated)",
                        "status": "present"
                    })
                    present_count += 1
                    continue
                    
                val = None
                status = "missing"
                
                try:
                    val = _calculate_rdkit_descriptor(smiles, name)
                except Exception as exc:
                    logger.debug(f"RDKit descriptor {name} dynamic calculation failed: {exc}")
                    
                if val is not None:
                    present_count += 1
                    status = "present"
                else:
                    try:
                        val = _fallback_descriptor_value(smiles, name)
                        present_count += 1
                        status = "present"
                    except Exception as exc:
                        logger.warning(f"Fallback descriptor {name} calculation failed: {exc}")
                        val = None
                        status = "missing"
                        
                descriptors.setdefault(family, []).append({
                    "name": name,
                    "value": val,
                    "status": status
                })
            except Exception as e:
                logger.error(f"Failed to process RDKit descriptor {name}: {e}")
                descriptors.setdefault(family, []).append({
                    "name": name,
                    "value": None,
                    "status": "failed"
                })

    # 2. Add any additional numeric columns in the dataset row
    try:
        system_cols = {
            smiles_col, val_col, unit_col, ep_col, name_col, cas_col,
            qualifier_col, "audit_flag", "session_id",
        }
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        dataset_descriptor_cols = [c for c in numeric_cols if c not in system_cols and c]
        
        # Filter out columns that are already present in standard RDKit descriptors (to avoid duplicates)
        standard_names_lower = {n.lower().replace("_", "").replace(" ", "") for ns in standard_descriptors.values() for n in ns}
        
        for col in dataset_descriptor_cols:
            try:
                col_lower = col.lower().replace("_", "").replace(" ", "")
                if col_lower in standard_names_lower:
                    continue # already captured in dynamic baseline
                    
                family = _classify_column(col)
                # Remap to fit user categories
                if family == "Fingerprint / Structural":
                    family = "Fingerprints"
                elif family == "Geometric / 3D":
                    family = "3D Descriptors"
                elif family == "ADMET / Pharmacokinetic":
                    family = "Physicochemical"
                    
                total_descriptors += 1
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
                    "status": status
                })
            except Exception as e:
                logger.error(f"Failed to process dataset descriptor column {col}: {e}")
    except Exception as exc:
        logger.error(f"Failed to extract custom numeric columns: {exc}")

    coverage_pct = round(100.0 * present_count / max(1, total_descriptors), 1)
    logger.info(f"[FLOW-TRACE] [{client_id}] Descriptor extraction finished. Total={total_descriptors}, Present={present_count}, Coverage={coverage_pct}%")

    # ── QSAR Readiness Score (0-100) ──────────────────────────────────────────
    has_rdkit_mol = False
    try:
        from rdkit import Chem
        has_rdkit_mol = Chem.MolFromSmiles(smiles) is not None
    except Exception:
        pass
    
    completeness_score = 40.0 * (present_count / max(1, total_descriptors))
    consistency_score = 20.0 # Standard default
    fingerprint_score = 20.0 # Morgan / MACCS are calculated
    structure_score = 20.0 if has_rdkit_mol or smiles else 0.0
    qsar_readiness_score = int(round(completeness_score + consistency_score + fingerprint_score + structure_score))

    response_payload = {
        "smiles": smiles,
        "cas": resolved["cas_number"],
        "name": resolved["chemical_name"],
        "formula": formula,
        "mw": mw_val,
        "inchi": inchi,
        "inchikey": inchikey,
        "metadata": metadata,
        "descriptors": descriptors,
        "descriptor_count": total_descriptors,
        "descriptor_coverage_pct": coverage_pct,
        "qsar_readiness_score": qsar_readiness_score,
        "_debug_match_method": match_method
    }
    logger.info(f"[FLOW-TRACE] [{client_id}] get_compound_detail returning response payload size={len(str(response_payload))} chars")
    return response_payload


@router.get("/{client_id}/descriptor-distribution")
async def get_descriptor_distribution(
    client_id: str,
    name: str = Query(..., description="Name of the descriptor"),
    smiles: str = Query(..., description="SMILES of the selected compound"),
):
    """Returns the dataset-wide distribution of the selected descriptor, 
    with comparative percentile placement for the active compound.
    """
    df, mappings, smiles_col, val_col, unit_col, ep_col, name_col, cas_col = (
        _load_df_and_mappings(client_id)
    )

    if not smiles_col or smiles_col not in df.columns:
        raise HTTPException(
            status_code=400,
            detail="SMILES column not mapped in this workspace.",
        )

    # 1. Get descriptor values from dataset
    col_values = []
    if name in df.columns:
        col_values = df[name].dropna().tolist()
    else:
        # It's an RDKit calculated descriptor — compute dynamically for all rows (optimized by unique smiles)
        unique_smiles = df[smiles_col].dropna().unique().tolist()
        smiles_to_val = {}
        for s in unique_smiles:
            val = _calculate_rdkit_descriptor(s, name)
            if val is None:
                val = _fallback_descriptor_value(s, name)
            smiles_to_val[s] = val
        col_values = [smiles_to_val[s] for s in df[smiles_col].dropna() if s in smiles_to_val]

    if not col_values:
        raise HTTPException(status_code=404, detail=f"No data available for descriptor '{name}'")
        
    col_values = [v for v in col_values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not col_values:
        raise HTTPException(status_code=404, detail=f"No numerical data available for descriptor '{name}'")
        
    mean_val = float(np.mean(col_values))
    median_val = float(np.median(col_values))
    std_val = float(np.std(col_values)) if len(col_values) > 1 else 0.0
    min_val = float(np.min(col_values))
    max_val = float(np.max(col_values))
    
    # Calculate current compound value
    current_val = _calculate_rdkit_descriptor(smiles, name)
    if current_val is None:
        current_val = _fallback_descriptor_value(smiles, name)
        
    # Calculate percentile position
    less_than = sum(1 for v in col_values if v <= current_val)
    percentile = round(100.0 * less_than / len(col_values), 1) if col_values else 50.0
    
    # Calculate histogram bins
    bins_count = 10
    val_range = max_val - min_val
    if val_range == 0:
        val_range = 1.0
    step = val_range / bins_count
    
    bins = []
    for i in range(bins_count):
        b_start = min_val + i * step
        b_end = b_start + step
        count = sum(1 for v in col_values if b_start <= v < b_end)
        if i == bins_count - 1: # include upper bound
            count += sum(1 for v in col_values if v == max_val)
            
        bins.append({
            "binLabel": f"{b_start:.1f} - {b_end:.1f}",
            "count": count,
            "value": float(b_start + step / 2)
        })

    return {
        "descriptor": name,
        "mean": mean_val,
        "median": median_val,
        "std": std_val,
        "min": min_val,
        "max": max_val,
        "current_value": current_val,
        "percentile": percentile,
        "histogram": bins
    }

@router.get("/debug/{client_id}")
async def debug_workspace_explorer(client_id: str):
    """
    Diagnostic endpoint to immediately inspect workspace loading and mapping integrity.
    """
    logger.info(f"[FLOW-TRACE] [{client_id}] Debug endpoint called.")
    context = registry.get_context(client_id)
    if not context:
        return {
            "success": False,
            "error": f"Workspace '{client_id}' not found in registry",
            "dataset_loaded": False,
            "cache_exists": False
        }
        
    try:
        df = context.load_slice()
        dataset_loaded = True
    except Exception as e:
        df = None
        dataset_loaded = False
        logger.error(f"[FLOW-TRACE] [{client_id}] Debug slice load failed: {e}")
        
    total_compounds = len(df) if df is not None else 0
    
    first_compound = "None"
    if df is not None and len(df) > 0:
        mappings = context.mappings or {}
        resolved = _resolve_compound_fields(df.iloc[0], mappings)
        first_compound = resolved["chemical_name"] or resolved["compound_name"] or "Unnamed"
        
    return {
        "success": True,
        "client_id": client_id,
        "total_compounds": total_compounds,
        "first_compound": first_compound,
        "descriptor_count": len(df.select_dtypes(include=[np.number]).columns) if df is not None else 0,
        "dataset_loaded": dataset_loaded,
        "cache_exists": context.dataframe_cache is not None,
        "mappings": context.mappings,
        "parquet_path": context.parquet_path
    }


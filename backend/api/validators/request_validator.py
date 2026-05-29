import os
import re
from typing import List, Dict
from pydantic import BaseModel, field_validator, model_validator
from fastapi import HTTPException

class BaseClientPayload(BaseModel):
    client_id: str

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Ensures the client_id/workspace_id matches safe alphanumeric patterns."""
        v = v.strip()
        if not v:
            raise ValueError("Workspace ID (client_id) cannot be empty.")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("Workspace ID must contain only alphanumeric characters, underscores, or dashes.")
        return v

class CurationPayload(BaseClientPayload):
    columns_to_drop: List[str]

    @field_validator("columns_to_drop")
    @classmethod
    def validate_columns(cls, v: List[str]) -> List[str]:
        """Sanitizes names of columns to drop."""
        return [c.strip() for c in v if c.strip()]

class MappingPayload(BaseClientPayload):
    mappings: Dict[str, str]

    @field_validator("mappings")
    @classmethod
    def validate_mappings_dict(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Ensures that the mapping values map to allowed scientific columns."""
        ALLOWED_SCI_VARS = {
            "none", "chemical_name", "chemical_id", "cas_number", "canonical_smiles", "inchi",
            "molecular_weight", "logp", "pka", "tpsa", "h_bond_donors", "h_bond_acceptors",
            "endpoint", "value", "unit", "qualifier", "pxc50", "assay_type", "target_gene", "cell_line",
            "organism", "strain", "life_stage", "trophic_level",
            "temperature", "ph", "study_year", "glp_compliant", "source_database", "test_type",
            "exposure_time", "exposure_route", "test_medium",
            "biodegradation", "half_life", "bcf", "koc",
            "patient_id", "age", "sex", "clinical_phase", "adverse_event",
            "clearance", "bioavailability", "cmax", "tmax", "vd",
            "smiles", "species", "duration", "ic50", "ec50", "ki", "potency", "toxicity", 
            "absorption", "distribution", "metabolism", "excretion", "toxicology", 
            "hbd", "hba", "rotatable_bonds", "target", "assay", "classification_target", "regression_target",
            "descriptor", "metabolite", "ghs_classification", "pubchem_cid", "chembl_id", "drugbank_id", 
            "dsstox_id", "echa_id", "molecular_formula", "inchikey"
        }
        
        # Translation map to normalize all scientific variables to canonical backend keys
        translation_map = {
            "smiles": "canonical_smiles",
            "inchi": "canonical_smiles",
            "chemical_id": "chemical_name",
            "organism": "species",
            "exposure_time": "duration",
            "pxc50": "value",
            "regression_target": "value",
            "pic50": "value",
            "potency": "value",
            "ic50": "value",
            "ec50": "value",
            "ki": "value",
            "classification_target": "endpoint",
            "assay": "endpoint",
            "assay_type": "endpoint",
            "target": "endpoint",
            "toxicity": "endpoint",
            "toxicology": "endpoint",
            "absorption": "endpoint",
            "distribution": "endpoint",
            "metabolism": "endpoint",
            "excretion": "endpoint"
        }
        
        sanitized = {}
        for col, sci_var in v.items():
            col = col.strip()
            sci_var = sci_var.strip().lower()
            if sci_var not in ALLOWED_SCI_VARS:
                raise ValueError(f"Mapping value '{sci_var}' is invalid. Allowed variables are: {list(ALLOWED_SCI_VARS)}")
            
            # Apply standard translations to align frontend/backend keys
            sci_var = translation_map.get(sci_var, sci_var)
            sanitized[col] = sci_var
            
        return sanitized

class SchemaInferPayload(BaseModel):
    columns: List[str]

    @field_validator("columns")
    @classmethod
    def validate_columns_list(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("Columns list cannot be empty.")
        return [c.strip() for c in v if c.strip()]

class SegregatePayload(BaseClientPayload):
    enable_dedup: bool = False
    enable_variance_pruning: bool = False
    prune_high_variance: bool = False
    selected_hierarchy: List[str] = []

    @field_validator("selected_hierarchy")
    @classmethod
    def validate_hierarchy(cls, v: List[str]) -> List[str]:
        return [c.strip() for c in v if c.strip()]

class EnrichmentPayload(BaseClientPayload):
    selected_descriptors: List[str]
    include_mordred: bool
    mode: str

    @field_validator("mode")
    @classmethod
    def validate_enrichment_mode(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("fast", "standard", "full"):
            raise ValueError("Enrichment mode must be 'fast', 'standard', or 'full'.")
        return v

def validate_uploaded_file(filename: str, size_in_bytes: int, content_type: str = None):
    """
    Validates uploaded files:
    - Supported extensions (.csv, .xlsx, .xlsm, .xls)
    - Max size limits from settings
    - Reject executables and invalid MIME types
    """
    from backend.core.config import settings
    max_size_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    supported_extensions = {".csv", ".xlsx", ".xlsm", ".xls"}
    executable_extensions = {".exe", ".bat", ".sh", ".cmd", ".msi", ".vbs", ".ps1"}
    
    if size_in_bytes > max_size_bytes:
        raise HTTPException(
            status_code=413, 
            detail=f"Uploaded file exceeds maximum limit of {settings.MAX_UPLOAD_MB}MB."
        )
        
    ext = os.path.splitext(filename)[1].lower() if "." in filename else ""
    
    if ext in executable_extensions:
        raise HTTPException(
            status_code=415,
            detail="Executable files are strictly prohibited."
        )
        
    if ext not in supported_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file format '{ext}'. Supported formats: {supported_extensions}"
        )
        
    if content_type:
        allowed_mimes = [
            "text/csv", 
            "application/vnd.ms-excel", 
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel.sheet.macroEnabled.12"
        ]
        if not any(mime in content_type.lower() for mime in allowed_mimes) and "application/octet-stream" not in content_type:
            raise HTTPException(
                status_code=415,
                detail=f"Invalid MIME type: {content_type}"
            )


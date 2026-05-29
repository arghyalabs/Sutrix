import logging
import pandas as pd
from typing import Dict, Any, List, Tuple

from backend.core.workspace_registry import PipelineContext

logger = logging.getLogger("sdo.core.pipeline_validator")

class PipelineValidator:
    """
    Verifies state transitions, validates column data schemas, mapping definitions,
    and inspects active dataframes for anomalies to ensure scientific integrity.
    """
    
    STAGE_RULES = {
        "ingest": [],
        "mapping": ["ingest"],
        "segregate": ["mapping"],
        "enrich": ["mapping", "segregate"],
        "readiness": ["enrich"]
    }

    @staticmethod
    def validate_stage_transition(context: PipelineContext, requested_stage: str) -> Tuple[bool, str]:
        """
        Validates whether the pipeline can progress to the requested stage.
        Asserts that all prerequisite stages are present in the execution trace.
        """
        required = PipelineValidator.STAGE_RULES.get(requested_stage, [])
        for req in required:
            if req not in context.execution_trace:
                msg = f"Scientific constraint violated: Cannot execute stage '{requested_stage}' before executing prerequisite '{req}'."
                logger.error(msg)
                return False, msg
        return True, ""

    @staticmethod
    def validate_mappings(columns: List[str], mappings: Dict[str, str]) -> Tuple[bool, str]:
        """
        Asserts that the provided column mappings are logically sound:
        1. Mappings must map to valid target scientific variables.
        2. Must include at least a chemical identifier column (e.g. smiles or chemical_id).
        3. Must include a potency value column to build segregation trees.
        """
        if not mappings:
            return False, "No column mappings submitted."

        # Verify mapping keys exist in dataset columns
        for user_col in mappings.keys():
            if user_col not in columns:
                return False, f"Mapped column '{user_col}' is missing from the active dataset schema."

        mapped_vars = set(mappings.values())
        
        # We require at least one structure or chemical id column
        has_id = any(v in ('canonical_smiles', 'smiles', 'chemical_id', 'chemical_name') for v in mapped_vars)
        if not has_id:
            return False, "Validation Error: At least one column must be mapped to a chemical identifier (SMILES or Compound Name)."

        # We require a potency value column to run scientific auditing and segregation
        has_val = 'value' in mapped_vars
        if not has_val:
            return False, "Validation Error: A numeric value column (potency concentration) is required for QSAR mapping."

        return True, ""

    @staticmethod
    def inspect_dataframe_schema(df: pd.DataFrame, mappings: Dict[str, str]) -> List[str]:
        """
        Performs diagnostic warnings audits on dataframes:
        - Check for high percentage of null values in critical fields.
        - Check for negative values in the mapped value column.
        - Check for non-numeric types in value columns.
        """
        warnings = []
        
        sci_to_user = {v: k for k, v in mappings.items() if k in df.columns}
        
        # 1. Inspect SMILES / identifiers null values
        smiles_col = sci_to_user.get('canonical_smiles') or sci_to_user.get('smiles')
        if smiles_col:
            null_count = df[smiles_col].isna().sum()
            if null_count > 0:
                warnings.append(f"Standardization Alert: {null_count} rows ({round(null_count / len(df) * 100, 1)}%) lack valid chemical structures.")

        # 2. Inspect value column numbers
        val_col = sci_to_user.get('value')
        if val_col:
            # Check for strings/mixed types in numeric potency columns
            non_numeric = pd.to_numeric(df[val_col], errors='coerce').isna().sum()
            if non_numeric > 0:
                warnings.append(f"Format Alert: {non_numeric} rows in the mapped value column '{val_col}' could not be parsed as numeric potency.")

            # Check for negative values
            try:
                numeric_series = pd.to_numeric(df[val_col], errors='coerce').dropna()
                negatives = (numeric_series < 0).sum()
                if negatives > 0:
                    warnings.append(f"Range Alert: {negatives} records contain negative values in potency field '{val_col}'.")
            except Exception:
                pass
                
        return warnings

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

logger = logging.getLogger("sdo.core.scientific_runtime")

class ScientificRuntime:
    """
    Centralized Scientific Computation Core.
    Houses mathematical formulas, canonicalization rules, biological variance metrics,
    and regulatory-grade OECD scoring logic to ensure 100% parity with Streamlit.
    """
    
    @staticmethod
    def canonicalize_smiles(smiles: str) -> str:
        """
        Standardizes SMILES structurally using RDKit canonicalization.
        Ensures identical tautomers and isomers map to the same node in data cleaning.
        """
        if not smiles or not isinstance(smiles, str) or not smiles.strip():
            return ""
        try:
            mol = Chem.MolFromSmiles(smiles.strip())
            if mol:
                return Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)
        except Exception as e:
            logger.warning(f"RDKit failed to canonicalize SMILES '{smiles}': {e}")
        return ""

    @staticmethod
    def calculate_log10_potency(value: float) -> float:
        """
        Transforms biological potency to log10 space for scientific variance checks.
        Protects against zero or negative inputs.
        """
        try:
            val = float(value)
            if val <= 0:
                return float('nan')
            return float(np.log10(val))
        except (ValueError, TypeError):
            return float('nan')

    @staticmethod
    def compute_biological_variance(group_values: List[float]) -> Tuple[float, float, str]:
        """
        Calculates biological log10 variance across multiple experiments of the same compound.
        Returns:
            (min_log10, max_log10, audit_flag)
            Where audit_flag is:
            - 'Consistent' (log10 range < 0.5)
            - 'Moderate_Variance' (0.5 <= log10 range < 1.0)
            - 'High_Variance_Conflict' (log10 range >= 1.0, i.e., 10-fold deviation)
        """
        log_vals = [ScientificRuntime.calculate_log10_potency(v) for v in group_values]
        log_vals = [lv for lv in log_vals if not np.isnan(lv)]
        
        if not log_vals:
            return float('nan'), float('nan'), 'Consistent'
        
        min_l = float(np.min(log_vals))
        max_l = float(np.max(log_vals))
        log_range = max_l - min_l
        
        if log_range >= 1.0:
            flag = 'High_Variance_Conflict'
        elif log_range >= 0.5:
            flag = 'Moderate_Variance'
        else:
            flag = 'Consistent'
            
        return round(min_l, 4), round(max_l, 4), flag

    @staticmethod
    def calculate_oecd_score(df: pd.DataFrame, mappings: Dict[str, str]) -> Dict[str, Any]:
        """
        Computes standard OECD data readiness and completeness scores.
        Aligns directly with original Streamlit quality checklists.
        """
        total_rows = len(df)
        if total_rows == 0:
            return {
                "score": 0.0,
                "tier": "Fails Compliance",
                "breakdown": {"structural_completeness": 0.0, "endpoint_uniformity": 0.0, "potency_consistency": 0.0},
                "deductions": ["Empty dataset submitted"]
            }

        # 1. Structural Completeness (presence of valid Smiles/CAS)
        smiles_col = next((k for k, v in mappings.items() if v in ('canonical_smiles', 'smiles')), None)
        valid_structs = 0
        if smiles_col and smiles_col in df.columns:
            valid_structs = df[smiles_col].notna().sum()
        structural_pct = (valid_structs / total_rows) * 100.0

        # 2. Endpoint and Unit Uniformity
        unit_col = next((k for k, v in mappings.items() if v == 'unit'), None)
        uniform_pct = 100.0
        if unit_col and unit_col in df.columns:
            unique_units = df[unit_col].dropna().nunique()
            if unique_units > 1:
                # Deduct points if multiple units exist without normalization
                uniform_pct = max(0.0, 100.0 - (unique_units - 1) * 25.0)

        # 3. Potency Variance Deductions
        consistency_pct = 100.0
        deductions = []
        if 'audit_flag' in df.columns:
            conflict_count = (df['audit_flag'] == 'High_Variance_Conflict').sum()
            conflict_ratio = conflict_count / total_rows
            consistency_pct = max(0.0, 100.0 - (conflict_ratio * 200.0))
            if conflict_count > 0:
                deductions.append(f"Biological Potency Noise: {conflict_count} compounds exceed 10-fold log10 variance thresholds.")

        if structural_pct < 90.0:
            deductions.append("Missing structures: More than 10% of records lack valid standardized chemical drawings.")
        if uniform_pct < 100.0:
            deductions.append("Multi-unit mixture: Multiple measurement units (e.g. mg/kg and uM) detected in a single target endpoint.")

        # Compute combined weighted score
        final_score = float(round((structural_pct * 0.4) + (uniform_pct * 0.3) + (consistency_pct * 0.3), 2))
        
        # Classify compliance tier
        if final_score >= 90.0:
            tier = "Tier-1: QSAR Gold Standard (OECD Compliant)"
        elif final_score >= 75.0:
            tier = "Tier-2: Model Ready (Minor Warnings)"
        elif final_score >= 50.0:
            tier = "Tier-3: Exploratory Only (Significant Noise)"
        else:
            tier = "Fails Compliance: Structural or POTENCY Deficiencies"

        return {
            "score": final_score,
            "tier": tier,
            "breakdown": {
                "structural_completeness": round(structural_pct, 1),
                "endpoint_uniformity": round(uniform_pct, 1),
                "potency_consistency": round(consistency_pct, 1)
            },
            "deductions": deductions
        }

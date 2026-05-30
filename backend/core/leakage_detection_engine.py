"""
Data Leakage Detection Engine.
Identifies identifier columns, suspiciously perfect feature-target correlations,
and duplicate structural compounds that could cause train/test leakage.
All outputs are JSON-serializable.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

IDENTIFIER_PATTERNS = [
    "id", "cas", "dtxsid", "smiles", "inchi", "name", "index",
    "row", "record", "cid", "sid", "uuid", "compound_id",
    "chemical_id", "sample_id", "substance_id", "molid",
]


class LeakageDetectionEngine:
    """Multi-signal data leakage detector for scientific ML datasets."""

    @staticmethod
    def detect_identifier_leakage(descriptor_cols: List[str]) -> List[Dict]:
        """
        Flags descriptor columns whose names suggest they are identifiers,
        not molecular descriptors. Identifiers should be dropped before modeling.
        """
        flagged = []
        for col in descriptor_cols:
            col_lower = col.lower()
            for pattern in IDENTIFIER_PATTERNS:
                if pattern in col_lower:
                    risk = "HIGH" if pattern in ("id", "cas", "inchi", "smiles") else "MEDIUM"
                    flagged.append({
                        "column": col,
                        "pattern_matched": pattern,
                        "risk": risk,
                        "recommendation": f"Remove '{col}' before modeling — it looks like an identifier, not a descriptor.",
                    })
                    break
        return flagged

    @staticmethod
    def detect_target_correlation_leakage(
        df: pd.DataFrame,
        descriptor_cols: List[str],
        target_col: str,
        threshold: float = 0.99,
    ) -> List[Dict]:
        """
        Flags features with near-perfect Pearson correlation to the target column.
        These are likely derived from the target (leakage).
        """
        if target_col not in df.columns:
            return []

        target_numeric = pd.to_numeric(df[target_col], errors="coerce")
        suspicious = []

        for col in descriptor_cols:
            if col == target_col:
                continue
            col_numeric = pd.to_numeric(df[col], errors="coerce")
            valid_mask = target_numeric.notna() & col_numeric.notna()
            if valid_mask.sum() < 10:
                continue
            try:
                r = float(target_numeric[valid_mask].corr(col_numeric[valid_mask]))
                if abs(r) >= threshold:
                    suspicious.append({
                        "feature": col,
                        "pearson_r": round(r, 4),
                        "abs_r": round(abs(r), 4),
                        "risk": "CRITICAL",
                        "recommendation": (
                            f"'{col}' has r={r:.4f} with target — may be derived from target. "
                            "Verify it is a valid predictor, not a data leakage source."
                        ),
                    })
            except Exception:
                continue

        return sorted(suspicious, key=lambda x: x["abs_r"], reverse=True)

    @staticmethod
    def detect_duplicate_leakage(
        df: pd.DataFrame, smiles_col: Optional[str]
    ) -> Dict[str, Any]:
        """
        Checks for structural duplicates (same SMILES) that could bleed between
        train and test sets in random splits.
        """
        if smiles_col is None or smiles_col not in df.columns:
            # Fall back to full row duplicates
            dup_count = int(df.duplicated().sum())
            total = len(df)
            dup_pct = round(dup_count / max(1, total) * 100, 2)
            risk_tier = (
                "CRITICAL" if dup_pct > 10 else
                "HIGH" if dup_pct > 5 else
                "MEDIUM" if dup_pct > 1 else
                "SAFE"
            )
            return {
                "duplicate_count": dup_count,
                "duplicate_pct": dup_pct,
                "risk_tier": risk_tier,
                "duplicate_smiles_sample": [],
                "note": "Based on full row duplicates (no SMILES column mapped).",
            }

        smiles_series = df[smiles_col].dropna().astype(str).str.strip()
        dup_mask = smiles_series.duplicated(keep=False)
        dup_smiles = smiles_series[dup_mask].unique().tolist()
        dup_count = int(dup_mask.sum())
        total = len(df)
        dup_pct = round(dup_count / max(1, total) * 100, 2)

        risk_tier = (
            "CRITICAL" if dup_pct > 10 else
            "HIGH" if dup_pct > 5 else
            "MEDIUM" if dup_pct > 1 else
            "SAFE"
        )

        return {
            "duplicate_count": dup_count,
            "duplicate_pct": dup_pct,
            "risk_tier": risk_tier,
            "duplicate_smiles_sample": [str(s) for s in dup_smiles[:10]],
            "note": (
                f"{dup_count} rows share SMILES with at least one other row. "
                "Use scaffold-aware train/test splitting to prevent leakage."
                if dup_count > 0 else
                "No structural duplicates detected."
            ),
        }

    @staticmethod
    def _compute_risk_score(
        identifier_leakage: List[Dict],
        target_leakage: List[Dict],
        duplicate_info: Dict,
    ) -> float:
        """Composite leakage risk score 0–100."""
        score = 0.0
        # Identifier columns: 8 pts each, max 40
        score += min(40.0, len(identifier_leakage) * 8.0)
        # Target correlations: 25 pts each, max 50
        score += min(50.0, len(target_leakage) * 25.0)
        # Duplicate leakage
        dup_tier = duplicate_info.get("risk_tier", "SAFE")
        dup_add = {"SAFE": 0, "MEDIUM": 5, "HIGH": 15, "CRITICAL": 25}.get(dup_tier, 0)
        score += dup_add
        return round(min(100.0, score), 1)

    @classmethod
    def run_full_analysis(
        cls,
        df: pd.DataFrame,
        descriptor_cols: List[str],
        target_col: Optional[str] = None,
        smiles_col: Optional[str] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Runs all leakage detectors and returns a unified report."""

        def _cb(pct, phase):
            if progress_callback:
                try:
                    progress_callback(pct, phase)
                except Exception:
                    pass

        _cb(20, "Checking identifier columns")
        identifier_leakage = cls.detect_identifier_leakage(descriptor_cols)

        _cb(45, "Correlation analysis with target")
        target_leakage = []
        if target_col:
            target_leakage = cls.detect_target_correlation_leakage(
                df, descriptor_cols, target_col
            )

        _cb(70, "Duplicate compound check")
        duplicate_info = cls.detect_duplicate_leakage(df, smiles_col)

        _cb(90, "Risk assessment")
        leakage_risk_score = cls._compute_risk_score(
            identifier_leakage, target_leakage, duplicate_info
        )
        risk_tier = (
            "CRITICAL" if leakage_risk_score > 75 else
            "HIGH" if leakage_risk_score > 50 else
            "MEDIUM" if leakage_risk_score > 20 else
            "SAFE"
        )

        _cb(100, "Complete")
        return {
            "identifier_columns": identifier_leakage,
            "suspicious_correlations": target_leakage,
            "duplicate_info": duplicate_info,
            "leakage_risk_score": leakage_risk_score,
            "risk_tier": risk_tier,
            "n_identifier_flags": len(identifier_leakage),
            "n_suspicious_correlations": len(target_leakage),
        }

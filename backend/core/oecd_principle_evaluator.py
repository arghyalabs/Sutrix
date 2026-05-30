"""
OECD QSAR Principle Evaluator — 5-principle compliance checker.
Evaluates whether a dataset meets OECD QSAR validation principles.
All outputs are JSON-serializable.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

# Descriptor families used for Principle 5 detection
_PHYSCHEM_KEYWORDS = ["logp", "tpsa", "hba", "hbd", "mw", "molwt", "mollogp", "rotatable"]
_TOPO_KEYWORDS = ["chi", "kappa", "balaban", "bertz", "estate", "slogp", "vsa", "ipc"]
_CONSTITUTIONAL_KEYWORDS = ["heavyatom", "ringcount", "numrings", "bondcount", "fractioncsp3"]


class OECDPrincipleEvaluator:
    """
    Evaluates OECD QSAR Principles 1–5 against the current dataset and returns
    a structured compliance report.
    """

    @staticmethod
    def evaluate_principle_1(df: pd.DataFrame, mappings: Dict) -> Dict:
        """
        Principle 1 — Defined Endpoint.
        PASS: endpoint col mapped + ≤2 unique endpoints + ≤2 unique units
        WARN: multiple endpoints or units
        FAIL: no endpoint mapped
        """
        sci_to_user = {v: k for k, v in mappings.items()}
        ep_col = sci_to_user.get("endpoint")
        unit_col = sci_to_user.get("unit")
        val_col = sci_to_user.get("value")

        score = 20  # base
        details_parts = []
        recommendations = []

        # Check endpoint column
        if ep_col and ep_col in df.columns:
            unique_eps = df[ep_col].dropna().astype(str).str.strip().unique()
            n_eps = len(unique_eps)
            score += 40
            if n_eps == 1:
                score += 15
                details_parts.append(f"Single endpoint: '{unique_eps[0]}'.")
            elif n_eps <= 3:
                details_parts.append(f"{n_eps} distinct endpoints detected: {list(unique_eps[:3])}.")
                recommendations.append("Segregate by endpoint before modeling for OECD compliance.")
            else:
                score -= 10
                details_parts.append(f"{n_eps} endpoints detected — high heterogeneity.")
                recommendations.append("Dataset contains mixed endpoints. Segregate or use multi-task modeling.")
        else:
            details_parts.append("No endpoint column mapped.")
            recommendations.append("Map the endpoint column (e.g. LC50, EC50) to the scientific field 'endpoint'.")

        # Check unit column
        if unit_col and unit_col in df.columns:
            unique_units = df[unit_col].dropna().astype(str).str.strip().unique()
            n_units = len(unique_units)
            score += 15
            if n_units == 1:
                score += 10
                details_parts.append(f"Consistent unit: '{unique_units[0]}'.")
            else:
                score -= 5
                details_parts.append(f"{n_units} different units present: {list(unique_units[:4])}.")
                recommendations.append("Normalize to a single unit before modeling (e.g. convert all to mg/L).")

        # Check value column
        if val_col and val_col in df.columns:
            n_missing_val = int(df[val_col].isna().sum())
            if n_missing_val == 0:
                details_parts.append("Target values complete — no missing potency data.")
            else:
                score -= 5
                details_parts.append(f"{n_missing_val} missing target values detected.")
                recommendations.append(f"Impute or remove {n_missing_val} missing target values.")

        score = max(0, min(100, score))
        status = "PASS" if score >= 75 else "WARN" if score >= 50 else "FAIL"

        return {
            "id": 1,
            "name": "Defined Endpoint",
            "status": status,
            "score": int(score),
            "details": " ".join(details_parts) or "Endpoint information could not be assessed.",
            "recommendations": recommendations,
        }

    @staticmethod
    def evaluate_principle_2(
        df: pd.DataFrame, descriptor_cols: List[str], mappings: Dict
    ) -> Dict:
        """
        Principle 2 — Unambiguous Algorithm.
        PASS: SMILES mapped + >3 descriptor families + no identifier columns
        WARN: partial
        FAIL: no descriptors
        """
        sci_to_user = {v: k for k, v in mappings.items()}
        smiles_col = sci_to_user.get("canonical_smiles")

        score = 20
        details_parts = []
        recommendations = []

        # SMILES column
        if smiles_col and smiles_col in df.columns:
            n_valid = int(df[smiles_col].notna().sum())
            score += 40
            details_parts.append(f"SMILES structures present ({n_valid} valid).")
        else:
            details_parts.append("No SMILES column mapped.")
            recommendations.append("Map canonical SMILES for full OECD algorithmic documentation.")

        # Descriptor count
        n_desc = len(descriptor_cols)
        if n_desc >= 50:
            score += 25
            details_parts.append(f"Large descriptor matrix ({n_desc} features) — comprehensive coverage.")
        elif n_desc >= 10:
            score += 15
            details_parts.append(f"{n_desc} descriptor columns present — moderate coverage.")
        elif n_desc > 0:
            score += 5
            details_parts.append(f"Only {n_desc} descriptor(s) — sparse coverage.")
            recommendations.append("Compute additional molecular descriptors using Mordred or RDKit for better coverage.")
        else:
            details_parts.append("No descriptor columns found.")
            recommendations.append("Run the Descriptor Enrichment step to compute Mordred/RDKit descriptors.")

        # Check for identifier columns
        from backend.core.leakage_detection_engine import IDENTIFIER_PATTERNS
        id_cols = [c for c in descriptor_cols if any(p in c.lower() for p in IDENTIFIER_PATTERNS)]
        if id_cols:
            score -= 10
            details_parts.append(f"{len(id_cols)} potential identifier column(s) in descriptor set.")
            recommendations.append(f"Remove identifier columns {id_cols[:3]} from the feature set.")

        score = max(0, min(100, score))
        status = "PASS" if score >= 75 else "WARN" if score >= 50 else "FAIL"

        return {
            "id": 2,
            "name": "Unambiguous Algorithm",
            "status": status,
            "score": int(score),
            "details": " ".join(details_parts) or "Algorithm definition could not be assessed.",
            "recommendations": recommendations,
        }

    @staticmethod
    def evaluate_principle_3(domain_result: Optional[Dict]) -> Dict:
        """
        Principle 3 — Applicability Domain.
        PASS: coverage_pct > 85%
        WARN: 70–85%
        FAIL: <70% or not computed
        """
        recommendations = []

        if domain_result is None:
            return {
                "id": 3,
                "name": "Applicability Domain",
                "status": "WARN",
                "score": 35,
                "details": (
                    "Applicability Domain has not been computed yet. "
                    "Run the 'AD Domain' analysis to evaluate domain coverage."
                ),
                "recommendations": [
                    "Run the Applicability Domain analysis (Williams Plot + kNN) to assess domain coverage.",
                    "OECD requires a defined AD for every QSAR model.",
                ],
            }

        coverage_pct = float(domain_result.get("domain_coverage_pct", 0.0))
        n_outside = int(domain_result.get("n_outside_domain", 0))
        h_star = float(domain_result.get("h_star", 0.0))

        if coverage_pct >= 85:
            score = 95
            status = "PASS"
            details = (
                f"{coverage_pct:.1f}% of compounds fall within the applicability domain "
                f"(h* = {h_star:.3f}). Domain is well-defined."
            )
        elif coverage_pct >= 70:
            score = 72
            status = "WARN"
            details = (
                f"{coverage_pct:.1f}% domain coverage. {n_outside} compounds outside domain boundary."
            )
            recommendations.append(f"Investigate {n_outside} out-of-domain compounds before deployment.")
        else:
            score = 40
            status = "FAIL"
            details = (
                f"Only {coverage_pct:.1f}% domain coverage. "
                f"{n_outside} compounds exceed the leverage threshold (h* = {h_star:.3f})."
            )
            recommendations.append("Consider removing or flagging out-of-domain compounds.")
            recommendations.append("Expand training set to cover broader chemical space.")

        return {
            "id": 3,
            "name": "Applicability Domain",
            "status": status,
            "score": int(score),
            "details": details,
            "recommendations": recommendations,
        }

    @staticmethod
    def evaluate_principle_4(
        n_samples: int, n_features: int, baseline_r2: Optional[float]
    ) -> Dict:
        """
        Principle 4 — Goodness of Fit.
        Based on N:P ratio and baseline predictive performance.
        """
        recommendations = []
        score = 20  # base
        details_parts = []

        ratio = n_samples / max(1, n_features)

        # N:P ratio scoring
        if ratio >= 10:
            score += 40
            details_parts.append(f"Safe N:P ratio of {ratio:.1f} — low overfitting risk.")
        elif ratio >= 3:
            score += 25
            details_parts.append(f"N:P ratio of {ratio:.1f} — moderate overfitting risk.")
            recommendations.append("Use regularization (L1/L2) and cross-validation with ≥5 folds.")
        else:
            score += 0
            details_parts.append(f"Low N:P ratio of {ratio:.1f} — high overfitting risk.")
            recommendations.append(
                f"N:P = {ratio:.1f} is critically low. "
                "Either reduce descriptor dimensionality or collect more compounds."
            )

        # Baseline R² scoring
        if baseline_r2 is not None:
            try:
                r2 = float(baseline_r2)
                if r2 >= 0.4:
                    score += 40
                    details_parts.append(f"Baseline R² = {r2:.3f} — strong predictive signal detected.")
                elif r2 >= 0.2:
                    score += 25
                    details_parts.append(f"Baseline R² = {r2:.3f} — moderate signal.")
                    recommendations.append("Consider feature selection (e.g. RFE) to improve signal-to-noise.")
                else:
                    score += 0
                    details_parts.append(f"Baseline R² = {r2:.3f} — weak predictive signal.")
                    recommendations.append(
                        "Weak baseline performance. Review endpoint quality and descriptor relevance."
                    )
            except Exception:
                details_parts.append("Baseline performance could not be parsed.")
        else:
            details_parts.append("Baseline performance not computed — run full AI Analysis first.")
            score = max(0, score - 5)

        score = max(0, min(100, score))
        status = "PASS" if score >= 75 else "WARN" if score >= 50 else "FAIL"

        return {
            "id": 4,
            "name": "Goodness of Fit",
            "status": status,
            "score": int(score),
            "details": " ".join(details_parts),
            "recommendations": recommendations,
        }

    @staticmethod
    def evaluate_principle_5(
        descriptor_cols: List[str], coverage_result: Optional[Dict]
    ) -> Dict:
        """
        Principle 5 — Mechanistic Interpretation.
        PASS: Physicochemical + Topological both present and ≥4 families
        WARN: only 1 family present
        FAIL: no recognizable descriptor families
        """
        recommendations = []
        score = 20
        details_parts = []

        # Detect descriptor families from column names
        desc_lower = [c.lower() for c in descriptor_cols]

        has_physchem = any(
            any(kw in c for kw in _PHYSCHEM_KEYWORDS) for c in desc_lower
        )
        has_topo = any(
            any(kw in c for kw in _TOPO_KEYWORDS) for c in desc_lower
        )
        has_constitutional = any(
            any(kw in c for kw in _CONSTITUTIONAL_KEYWORDS) for c in desc_lower
        )

        # Use coverage_result if available for richer analysis
        n_families = 0
        if coverage_result:
            families = coverage_result.get("families", [])
            present_families = [f for f in families if f.get("present", 0) > 0]
            n_families = len(present_families)
            family_names = [f["name"] for f in present_families]
            details_parts.append(
                f"{n_families} descriptor families detected: {', '.join(family_names[:5])}."
            )
        else:
            # Estimate from keywords
            n_families = sum([has_physchem, has_topo, has_constitutional])
            details_parts.append(
                f"~{n_families} descriptor family types detected from column names."
            )

        if has_physchem:
            score += 40
            details_parts.append("Physicochemical descriptors present (LogP, TPSA, HBA/HBD).")
        else:
            recommendations.append(
                "Add physicochemical descriptors (LogP, TPSA, HBA, HBD) for mechanistic interpretation."
            )

        if has_topo:
            score += 30
            details_parts.append("Topological descriptors present (Chi, Kappa, Balaban indices).")
        else:
            recommendations.append(
                "Add topological descriptors (Chi indices, Kappa shape indices) for graph-based SAR."
            )

        if n_families >= 4:
            score += 10
            details_parts.append("Multi-family descriptor coverage supports mechanistic QSAR interpretation.")
        elif n_families == 0:
            score = 15
            details_parts.append("No recognizable descriptor families found.")
            recommendations.append("Compute molecular descriptors using Mordred or RDKit for scientific interpretability.")

        score = max(0, min(100, score))
        status = "PASS" if score >= 75 else "WARN" if score >= 50 else "FAIL"

        return {
            "id": 5,
            "name": "Mechanistic Interpretation",
            "status": status,
            "score": int(score),
            "details": " ".join(details_parts) or "Descriptor interpretability could not be assessed.",
            "recommendations": recommendations,
        }

    @classmethod
    def run_full_evaluation(
        cls,
        df: pd.DataFrame,
        mappings: Dict = None,
        descriptor_cols: List[str] = None,
        n_samples: int = 0,
        n_features: int = 0,
        domain_result: Optional[Dict] = None,
        coverage_result: Optional[Dict] = None,
        baseline_r2: Optional[float] = None,
        progress_callback=None,
        **kwargs,  # absorb extra params like smiles_col, label_col from API route
    ) -> Dict[str, Any]:
        # Resolve defaults
        if mappings is None:
            mappings = {}
        if descriptor_cols is None:
            descriptor_cols = []
        if n_samples == 0 and df is not None and not df.empty:
            n_samples = len(df)
        if n_features == 0:
            n_features = len(descriptor_cols)
        """
        Evaluates all 5 OECD QSAR principles and returns a compliance report.
        """
        def _cb(pct, phase):
            if progress_callback:
                try:
                    progress_callback(pct, phase)
                except Exception:
                    pass

        _cb(20, "Principle 1: Defined Endpoint")
        p1 = cls.evaluate_principle_1(df, mappings)

        _cb(35, "Principle 2: Unambiguous Algorithm")
        p2 = cls.evaluate_principle_2(df, descriptor_cols, mappings)

        _cb(50, "Principle 3: Applicability Domain")
        p3 = cls.evaluate_principle_3(domain_result)

        _cb(65, "Principle 4: Goodness of Fit")
        p4 = cls.evaluate_principle_4(n_samples, n_features, baseline_r2)

        _cb(80, "Principle 5: Mechanistic Interpretation")
        p5 = cls.evaluate_principle_5(descriptor_cols, coverage_result)

        _cb(95, "Computing overall score")
        principles = [p1, p2, p3, p4, p5]
        overall_score = int(round(sum(p["score"] for p in principles) / 5))

        pass_count = sum(1 for p in principles if p["status"] == "PASS")
        warn_count = sum(1 for p in principles if p["status"] == "WARN")
        fail_count = sum(1 for p in principles if p["status"] == "FAIL")

        compliance_tier = (
            "FULLY_COMPLIANT" if pass_count == 5 else
            "PARTIAL_COMPLIANT" if pass_count >= 3 else
            "NON_COMPLIANT"
        )

        _cb(100, "Complete")

        return {
            "principles": principles,
            "overall_oecd_score": overall_score,
            "pass_count": pass_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
            "compliance_tier": compliance_tier,
        }

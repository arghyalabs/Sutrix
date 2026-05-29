"""
Modeling Routes — /api/modeling/* endpoints.
Orchestrates all existing + new analysis engines into a single unified response.
"""
import logging
import io
import json
import time
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.validators.request_validator import BaseClientPayload
from backend.core.workspace_registry import registry

# Existing engines (already built)
from backend.processing.readiness_engine import (
    DatasetReadinessScorer,
    DescriptorReliabilityEngine,
    ChemicalDiversityScorer,
    ScaffoldLeakageAuditor,
    SuccessEstimator,
    ScientificIntelligenceEngine,
)
from backend.intelligence.missingness_analysis import MissingnessAnalysis
from backend.intelligence.descriptor_correlation import DescriptorCorrelation
from backend.intelligence.duplicate_detection import DuplicateDetection
from backend.intelligence.conflict_detection import ConflictDetection
from backend.intelligence.dataset_health import DatasetHealthIntelligence

# New thin engines
from backend.core.modeling_risk_engine import assess_modeling_risks
from backend.core.model_recommender import recommend_models
from backend.core.feature_engineering_advisor import advise_features

logger = logging.getLogger("sdo.api.modeling")
router = APIRouter(prefix="/api/modeling", tags=["modeling"])

# In-memory cache keyed by client_id
_results_cache: Dict[str, Dict[str, Any]] = {}


def _safe_float(val, default=0.0):
    try:
        f = float(val)
        return f if np.isfinite(f) else default
    except Exception:
        return default


def _resolve_columns(df: pd.DataFrame, mappings: Dict[str, str]):
    """Returns useful column groups from mappings."""
    sci_to_user = {v: k for k, v in mappings.items()}
    smiles_col = sci_to_user.get("canonical_smiles")
    val_col = sci_to_user.get("value")
    unit_col = sci_to_user.get("unit")
    ep_col = sci_to_user.get("endpoint")

    system_cols = [smiles_col, val_col, unit_col, ep_col, "audit_flag", "session_id"]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    descriptor_cols = [c for c in numeric_cols if c not in system_cols and c]

    return smiles_col, val_col, unit_col, ep_col, descriptor_cols


def _compute_feasibility(readiness_score: float, diversity: Dict, success: Dict, descriptor_rel: Dict, n: int, p: int) -> Dict:
    """Builds radar chart data for the 6-axis feasibility panel."""
    ratio = n / max(1, p)

    # Model Stability: based on N/P ratio + variance quality
    stability = min(100, ratio * 15 + 30)

    # Reproducibility: diversity + scaffold leakage
    scaf = diversity.get("scaffold_imbalance_level", "")
    repro = 80 if "Low" in scaf else (55 if "Moderate" in scaf else 30)

    # Generalization: success estimator confidence
    conf = success.get("confidence", "Low")
    if "High" in conf:
        generaliz = 80
    elif "Moderate" in conf:
        generaliz = 55
    else:
        generaliz = 30

    # Descriptor Richness: reliability score
    desc_score = _safe_float(descriptor_rel.get("descriptor_reliability_score", 50))

    # Chemical Diversity
    chem_div = _safe_float(diversity.get("chemical_diversity_score", 0.5)) * 100

    # Data Balance: from readiness breakdown
    balance = min(100, readiness_score * 0.9)

    axes = ["Model Stability", "Reproducibility", "Generalization", "Descriptor Richness", "Chemical Diversity", "Data Balance"]
    values = [
        min(100, round(stability, 1)),
        round(repro, 1),
        round(generaliz, 1),
        round(desc_score, 1),
        round(chem_div, 1),
        round(balance, 1),
    ]
    lower = [max(0, v - 12) for v in values]
    upper = [min(100, v + 12) for v in values]

    mean_val = sum(values) / len(values)
    if mean_val >= 70:
        interpretation = "Dataset shows strong modeling potential. Proceed to model selection and cross-validation."
    elif mean_val >= 50:
        interpretation = "Dataset shows moderate modeling potential. Address feature engineering recommendations before training."
    else:
        interpretation = "Dataset has significant quality gaps. Resolve CRITICAL issues before attempting QSAR modeling."

    return {
        "axes": axes,
        "values": values,
        "confidence_lower": lower,
        "confidence_upper": upper,
        "interpretation": interpretation,
        "mean_score": round(mean_val, 1),
    }


def _build_oecd_checks(mappings: Dict[str, str], harmonization: Dict, df: pd.DataFrame) -> List[Dict]:
    """Evaluates OECD 5-principle readiness."""
    sci_to_user = {v: k for k, v in mappings.items()}
    ep_col = sci_to_user.get("endpoint")
    smiles_col = sci_to_user.get("canonical_smiles")
    val_col = sci_to_user.get("value")

    checks = []

    # 1. Defined endpoint
    has_ep = ep_col and ep_col in df.columns and df[ep_col].notna().sum() > 0
    checks.append({
        "principle": 1, "name": "Defined Endpoint",
        "status": bool(has_ep),
        "evidence": f"Endpoint column '{ep_col}' is mapped with {df[ep_col].notna().sum() if has_ep else 0} non-null values." if has_ep else "No endpoint column mapped. Assign the 'endpoint' role in the Mapping step.",
    })

    # 2. Unambiguous algorithm readiness
    has_smiles = smiles_col and smiles_col in df.columns and df[smiles_col].notna().sum() > 0
    has_val = val_col and val_col in df.columns
    checks.append({
        "principle": 2, "name": "Unambiguous Algorithm Readiness",
        "status": bool(has_smiles and has_val),
        "evidence": "Structural SMILES and target values are available for supervised QSAR training." if (has_smiles and has_val) else "Missing SMILES or target values. Structural inputs are required for deterministic QSAR algorithms.",
    })

    # 3. Applicability domain
    findings = harmonization.get("findings", [])
    mixed_units = any(f.get("issue") == "Mixed Assay Units Detected" for f in findings)
    checks.append({
        "principle": 3, "name": "Applicability Domain Suitability",
        "status": not mixed_units,
        "evidence": "Unit harmonization passed. Chemical space is consistently measured." if not mixed_units else "Mixed assay units detected. Applicability domain cannot be reliably defined across incompatible measurement scales.",
    })

    # 4. Mechanistic interpretability
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    exclude = [val_col, smiles_col]
    desc_count = len([c for c in numeric_cols if c not in exclude])
    interpretable = desc_count >= 5
    checks.append({
        "principle": 4, "name": "Mechanistic Interpretability Potential",
        "status": interpretable,
        "evidence": f"{desc_count} numerical descriptors available. Feature importance analysis will be possible." if interpretable else "Insufficient descriptor coverage for mechanistic interpretation. Run the Enrichment step.",
    })

    # 5. Data consistency
    mixed_eps = any(f.get("issue") == "Mixed Biological Endpoints" for f in findings)
    checks.append({
        "principle": 5, "name": "Data Consistency",
        "status": not mixed_eps,
        "evidence": "Single biological endpoint detected. Data is internally consistent." if not mixed_eps else "Multiple biological endpoints present. Segregate by endpoint before modeling or use multi-task architectures.",
    })

    return checks


def _build_viz_data(df: pd.DataFrame, smiles_col, val_col, ep_col, descriptor_cols: List[str]) -> Dict:
    """Builds lightweight summary data for frontend charts. Never returns raw rows."""
    viz = {}

    # Missing heatmap: sample up to 50 descriptors × 200 rows
    sample_desc = descriptor_cols[:50]
    sample_rows = min(200, len(df))
    if sample_desc and sample_rows > 0:
        hm_df = df[sample_desc].iloc[:sample_rows].isnull().astype(int)
        viz["missing_heatmap"] = {
            "z": hm_df.values.tolist(),
            "x": sample_desc,
            "y": list(range(sample_rows)),
        }

    # Endpoint distribution
    if val_col and val_col in df.columns:
        vals = pd.to_numeric(df[val_col], errors="coerce").dropna()
        if len(vals) > 0:
            counts, bins = np.histogram(vals, bins=min(30, len(vals)))
            viz["endpoint_distribution"] = {
                "values": vals.tolist()[:2000],
                "bin_edges": bins.tolist(),
                "counts": counts.tolist(),
            }

    # Variance data (top 40 descriptors by variance)
    if descriptor_cols:
        num_df = df[descriptor_cols].apply(pd.to_numeric, errors="coerce")
        variances = num_df.var().dropna().sort_values(ascending=False)
        top = variances.head(40)
        viz["variance_data"] = {
            "names": top.index.tolist(),
            "variances": [round(float(v), 4) for v in top.values],
        }

    # Class balance (endpoint column categories)
    if ep_col and ep_col in df.columns:
        vc = df[ep_col].value_counts()
        viz["class_balance"] = {
            "labels": vc.index.tolist()[:20],
            "counts": vc.values.tolist()[:20],
        }

    # Correlation matrix (top 25 descriptors by variance)
    if descriptor_cols:
        top25 = descriptor_cols[:25]
        num_df = df[top25].apply(pd.to_numeric, errors="coerce")
        corr = num_df.corr(method="pearson")
        viz["correlation_matrix"] = {
            "z": [[round(float(v), 3) if pd.notna(v) else 0 for v in row] for row in corr.values],
            "labels": top25,
        }

    # Outlier data (first 2 numeric descriptors vs endpoint)
    if descriptor_cols and val_col and val_col in df.columns:
        x_col = descriptor_cols[0]
        y_vals = pd.to_numeric(df[val_col], errors="coerce")
        x_vals = pd.to_numeric(df[x_col], errors="coerce")
        valid = x_vals.notna() & y_vals.notna()
        if valid.sum() > 0:
            xv = x_vals[valid]
            yv = y_vals[valid]
            q1, q3 = yv.quantile(0.25), yv.quantile(0.75)
            iqr = q3 - q1
            is_out = ((yv < q1 - 1.5 * iqr) | (yv > q3 + 1.5 * iqr)).tolist()
            viz["outliers"] = {
                "x": xv.tolist()[:1000],
                "y": yv.tolist()[:1000],
                "x_label": x_col,
                "y_label": val_col,
                "is_outlier": is_out[:1000],
            }

    return viz


@router.post("/analyze")
async def run_modeling_analysis(payload: BaseClientPayload):
    """Runs all analysis engines and caches results."""
    client_id = payload.client_id
    ctx = registry.get_context(client_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Workspace not found. Upload a dataset first.")

    parquet_path = ctx.descriptor_dataframe_path or ctx.mapped_dataframe_path or ctx.parquet_path
    if not parquet_path:
        raise HTTPException(status_code=400, detail="No enriched dataset available. Complete the Enrichment step first.")

    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset: {e}")

    mappings = ctx.mappings or {}
    smiles_col, val_col, unit_col, ep_col, descriptor_cols = _resolve_columns(df, mappings)
    n, p = len(df), len(descriptor_cols)

    t0 = time.time()
    logger.info(f"[{client_id}] Starting modeling analysis. N={n}, P={p}")

    # ── 1. Run all existing engines ─────────────────────────────────────────
    try:
        readiness_raw = DatasetReadinessScorer().evaluate(df, mappings)
    except Exception as e:
        logger.warning(f"DatasetReadinessScorer failed: {e}")
        readiness_raw = {"score": 0, "tier": "Unknown", "breakdown": {}, "deductions": []}

    try:
        descriptor_rel = DescriptorReliabilityEngine.evaluate_descriptors(df, mappings)
    except Exception as e:
        logger.warning(f"DescriptorReliabilityEngine failed: {e}")
        descriptor_rel = {"keep": [], "moderate_warning": [], "recommend_pruning": [], "hard_exclusion": [], "descriptor_reliability_score": 0}

    try:
        diversity = ChemicalDiversityScorer.calculate_diversity(df, mappings)
    except Exception as e:
        logger.warning(f"ChemicalDiversityScorer failed: {e}")
        diversity = {"status": "Skipped", "chemical_diversity_score": 0.5, "mean_tanimoto_similarity": 0.5, "interpretation": ""}

    try:
        scaffold = ScaffoldLeakageAuditor.audit_scaffolds(df, mappings)
    except Exception as e:
        logger.warning(f"ScaffoldLeakageAuditor failed: {e}")
        scaffold = {"status": "Skipped", "scaffold_imbalance_level": "Unknown", "details": ""}

    # Merge scaffold into diversity result for downstream use
    diversity["scaffold_imbalance_level"] = scaffold.get("scaffold_imbalance_level", "Unknown")
    diversity["scaffold_details"] = scaffold.get("details", "")

    try:
        success_est = SuccessEstimator.run_level1_quick(df, mappings)
    except Exception as e:
        logger.warning(f"SuccessEstimator failed: {e}")
        success_est = {"confidence": "Low", "baseline_performance": 0.0, "reason": str(e)}

    try:
        harmonization = ScientificIntelligenceEngine.audit_endpoint_harmonization(df, mappings)
    except Exception as e:
        logger.warning(f"Harmonization failed: {e}")
        harmonization = {"harmonized": True, "findings": []}

    try:
        noise_res = ScientificIntelligenceEngine.detect_experimental_noise(df, mappings)
    except Exception as e:
        logger.warning(f"Noise detection failed: {e}")
        noise_res = {"noise_detected": False, "conflicts": []}

    try:
        missingness = MissingnessAnalysis.analyze(df, target_cols=descriptor_cols[:100] if descriptor_cols else None)
        missingness.pop("figure", None)  # don't serialize plotly Figure
    except Exception as e:
        logger.warning(f"MissingnessAnalysis failed: {e}")
        missingness = {"overall_missing_pct": 0, "column_missingness": []}

    try:
        correlations = DescriptorCorrelation.analyze(df, descriptor_cols[:50])
        correlations.pop("figure", None)
    except Exception as e:
        logger.warning(f"DescriptorCorrelation failed: {e}")
        correlations = {"redundant_pairs": [], "redundant_count": 0}

    try:
        duplicates = DuplicateDetection.analyze(df, smiles_col or "", val_col or "")
    except Exception as e:
        logger.warning(f"DuplicateDetection failed: {e}")
        duplicates = {"exact_duplicates": 0, "duplicate_groups": 0}

    try:
        conflicts = ConflictDetection.analyze(df, smiles_col or "", val_col or "")
    except Exception as e:
        logger.warning(f"ConflictDetection failed: {e}")
        conflicts = {"conflicts_count": 0, "conflict_groups": 0, "details": []}

    health_metrics = {
        "total_rows": n,
        "missingness": missingness,
        "duplicates": duplicates,
        "conflicts": conflicts,
        "correlations": correlations,
    }

    # ── 2. New thin engines ──────────────────────────────────────────────────
    try:
        risks = assess_modeling_risks(readiness_raw, diversity, success_est, descriptor_rel, health_metrics, n, p)
    except Exception as e:
        logger.warning(f"Risk engine failed: {e}")
        risks = []

    try:
        # Determine endpoint type
        if val_col and val_col in df.columns:
            uniq = pd.to_numeric(df[val_col], errors="coerce").dropna().nunique()
            ep_type = "classification" if uniq <= 5 else "regression"
        else:
            ep_type = "unknown"
        class_bal = _safe_float(readiness_raw.get("breakdown", {}).get("class_balance", 50))
        div_score = _safe_float(diversity.get("chemical_diversity_score", 0.5))
        models = recommend_models(n, p, ep_type, class_bal, div_score)
    except Exception as e:
        logger.warning(f"ModelRecommender failed: {e}")
        models = []

    try:
        features = advise_features(df, mappings, descriptor_rel, missingness, correlations)
    except Exception as e:
        logger.warning(f"FeatureAdvisor failed: {e}")
        features = []

    # ── 3. Composite scores ──────────────────────────────────────────────────
    raw_score = _safe_float(readiness_raw.get("score", 0))
    desc_rel_score = _safe_float(descriptor_rel.get("descriptor_reliability_score", 50))
    div_score_pct = _safe_float(diversity.get("chemical_diversity_score", 0.5)) * 100
    baseline_perf = _safe_float(success_est.get("baseline_performance", 0))

    ai_score = round(raw_score, 1)
    qsar_score = round((raw_score * 0.5 + desc_rel_score * 0.3 + div_score_pct * 0.2), 1)
    stability_score = round((raw_score * 0.4 + (100 - len(risks) * 8) * 0.3 + desc_rel_score * 0.3), 1)
    integrity_score = round((raw_score * 0.6 + (100 if harmonization.get("harmonized") else 60) * 0.4), 1)

    for s in [ai_score, qsar_score, stability_score, integrity_score]:
        s = max(0, min(100, s))

    if ai_score >= 80:
        confidence_tier = "HIGH"
    elif ai_score >= 60:
        confidence_tier = "MEDIUM"
    elif ai_score >= 40:
        confidence_tier = "LOW"
    else:
        confidence_tier = "INSUFFICIENT"

    # ── 4. OECD checks ───────────────────────────────────────────────────────
    try:
        oecd_checks = _build_oecd_checks(mappings, harmonization, df)
    except Exception as e:
        logger.warning(f"OECD checks failed: {e}")
        oecd_checks = []

    # Descriptor readiness by category
    descriptor_readiness = [
        {"category": "Keep (complete)", "count": len(descriptor_rel.get("keep", [])), "completeness": 100, "recommendation": "Include as-is"},
        {"category": "Moderate Warning", "count": len(descriptor_rel.get("moderate_warning", [])), "completeness": 75, "recommendation": "Monitor or impute"},
        {"category": "Recommend Pruning", "count": len(descriptor_rel.get("recommend_pruning", [])), "completeness": 45, "recommendation": "Drop or impute"},
        {"category": "Hard Exclusion", "count": len(descriptor_rel.get("hard_exclusion", [])), "completeness": 15, "recommendation": "Remove immediately"},
    ]

    # Quality anomalies from noise + conflicts
    anomalies = []
    if noise_res.get("noise_detected"):
        for c in noise_res.get("conflicts", [])[:20]:
            anomalies.append({
                "type": "Conflicting Endpoint", "severity": "HIGH",
                "affected_rows": c.get("count", 2),
                "description": f"Compound '{str(c.get('compound','?'))[:40]}' has {c.get('count')} measurements spanning {c.get('log_range',0):.1f} log-units.",
                "suggested_action": "Review assay conditions. Average or flag for exclusion.",
            })
    if conflicts.get("conflict_groups", 0) > 0:
        anomalies.append({
            "type": "Structural Conflicts", "severity": "HIGH",
            "affected_rows": conflicts.get("conflicts_count", 0),
            "description": f"{conflicts.get('conflict_groups')} structural groups have conflicting biological endpoint values.",
            "suggested_action": "Deduplicate by taking mean or median endpoint per compound.",
        })

    quality_funnel = [
        {"stage": "Raw Rows", "count": n},
        {"stage": "After Dedup", "count": n - duplicates.get("exact_duplicates", 0)},
        {"stage": "After Outlier Removal (est.)", "count": max(0, n - int(n * 0.05))},
        {"stage": "After Conflict Resolution", "count": max(0, n - conflicts.get("conflicts_count", 0))},
    ]

    # ── 5. Build viz data ────────────────────────────────────────────────────
    try:
        viz_data = _build_viz_data(df, smiles_col, val_col, ep_col, descriptor_cols)
    except Exception as e:
        logger.warning(f"Viz data build failed: {e}")
        viz_data = {}

    # ── 6. Feasibility ───────────────────────────────────────────────────────
    feasibility = _compute_feasibility(raw_score, diversity, success_est, descriptor_rel, n, p)

    elapsed = round(time.time() - t0, 2)
    logger.info(f"[{client_id}] Modeling analysis done in {elapsed}s. AI Score={ai_score}")

    result = {
        "readiness": {
            "ai_score": ai_score,
            "qsar_score": min(100, qsar_score),
            "stability_score": min(100, max(0, stability_score)),
            "integrity_score": min(100, max(0, integrity_score)),
            "confidence_tier": confidence_tier,
            "breakdown": readiness_raw.get("breakdown", {}),
            "deductions": readiness_raw.get("deductions", []),
            "tier": readiness_raw.get("tier", "Unknown"),
            "diversity_score": round(div_score_pct, 1),
            "descriptor_reliability_score": round(desc_rel_score, 1),
            "baseline_performance": round(baseline_perf * 100, 1),
            "success_confidence": success_est.get("confidence", "Unknown"),
            "n_samples": n,
            "n_features": p,
            "n_to_p_ratio": round(n / max(1, p), 2),
        },
        "feasibility": feasibility,
        "qsar": {
            "oecd_checks": oecd_checks,
            "descriptor_readiness": descriptor_readiness,
            "endpoint_status": {
                "harmonized": harmonization.get("harmonized", True),
                "findings": harmonization.get("findings", []),
            },
            "overall_oecd_tier": readiness_raw.get("tier", "Unknown"),
            "oecd_pass_count": sum(1 for c in oecd_checks if c["status"]),
        },
        "features": features,
        "models": models,
        "quality": {
            "anomalies": anomalies,
            "funnel": quality_funnel,
            "health_score": DatasetHealthIntelligence.calculate_health_score(health_metrics),
            "recommendations": DatasetHealthIntelligence.generate_recommendations(health_metrics),
        },
        "risks": risks,
        "visualizations": viz_data,
        "meta": {
            "elapsed_seconds": elapsed,
            "n_samples": n,
            "n_features": p,
            "analysis_timestamp": time.time(),
        },
    }

    _results_cache[client_id] = result
    ctx.readiness_results = {"modeling_analysis": result}
    return result


@router.get("/{client_id}/results")
async def get_modeling_results(client_id: str):
    """Returns cached modeling analysis results."""
    if client_id in _results_cache:
        return _results_cache[client_id]

    # Try workspace registry
    ctx = registry.get_context(client_id)
    if ctx and ctx.readiness_results.get("modeling_analysis"):
        return ctx.readiness_results["modeling_analysis"]

    raise HTTPException(status_code=404, detail="No analysis results found. Run /api/modeling/analyze first.")


@router.post("/{client_id}/export")
async def export_modeling_report(client_id: str, format: str = "json"):
    """Exports the modeling analysis report in json, csv, or xlsx."""
    if client_id not in _results_cache:
        raise HTTPException(status_code=404, detail="No results to export.")

    result = _results_cache[client_id]

    if format == "json":
        content = json.dumps(result, indent=2, default=str)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=sdo_modeling_report_{client_id}.json"},
        )

    elif format == "csv":
        rows = []
        r = result["readiness"]
        rows.append({"metric": "AI Readiness Score", "value": r["ai_score"]})
        rows.append({"metric": "QSAR Readiness Score", "value": r["qsar_score"]})
        rows.append({"metric": "Stability Score", "value": r["stability_score"]})
        rows.append({"metric": "Integrity Score", "value": r["integrity_score"]})
        rows.append({"metric": "Confidence Tier", "value": r["confidence_tier"]})
        rows.append({"metric": "N Samples", "value": r["n_samples"]})
        rows.append({"metric": "N Features", "value": r["n_features"]})
        for risk in result.get("risks", []):
            rows.append({"metric": f"Risk: {risk['risk']}", "value": risk["severity"]})
        df_out = pd.DataFrame(rows)
        buf = io.StringIO()
        df_out.to_csv(buf, index=False)
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=sdo_modeling_report_{client_id}.csv"},
        )

    elif format == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            # Scores sheet
            scores = result["readiness"]
            pd.DataFrame([{
                "AI Score": scores["ai_score"], "QSAR Score": scores["qsar_score"],
                "Stability": scores["stability_score"], "Integrity": scores["integrity_score"],
                "Tier": scores["confidence_tier"], "N": scores["n_samples"], "P": scores["n_features"],
            }]).to_excel(writer, sheet_name="Scores", index=False)
            # Risks
            risks_df = pd.DataFrame(result.get("risks", []))
            if not risks_df.empty:
                risks_df[["risk", "severity", "impact", "mitigation", "affected_stage"]].to_excel(writer, sheet_name="Risks", index=False)
            # Features
            feat_df = pd.DataFrame(result.get("features", []))
            if not feat_df.empty:
                feat_df[["action", "severity", "reasoning", "expected_impact"]].to_excel(writer, sheet_name="Feature Advisor", index=False)
            # Models
            models_df = pd.DataFrame(result.get("models", []))
            if not models_df.empty:
                models_df[["algorithm", "category", "suitability_score", "expected_robustness", "scientific_reasoning"]].to_excel(writer, sheet_name="Model Recommendations", index=False)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=sdo_modeling_report_{client_id}.xlsx"},
        )

    raise HTTPException(status_code=400, detail="Unsupported format. Use: json, csv, xlsx")

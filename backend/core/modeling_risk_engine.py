"""
Modeling Risk Engine — classifies dataset risks for predictive modeling.
Inputs are pre-computed metrics from existing engines.
"""
from typing import Dict, Any, List


def assess_modeling_risks(
    readiness_result: Dict[str, Any],
    diversity_result: Dict[str, Any],
    success_result: Dict[str, Any],
    descriptor_result: Dict[str, Any],
    health_metrics: Dict[str, Any],
    n_samples: int,
    n_features: int,
) -> List[Dict[str, Any]]:
    """Produces a prioritized risk matrix from pre-computed analysis results."""
    risks = []
    ratio = n_samples / max(1, n_features)

    # 1. Small sample instability
    if n_samples < 50:
        risks.append({
            "risk": "Small Sample Instability",
            "severity": "CRITICAL",
            "probability": 0.95,
            "impact": "Model variance will be extremely high. Any result is statistically unreliable.",
            "mitigation": "Collect ≥100 additional data points before attempting QSAR modeling.",
            "affected_stage": "Training"
        })
    elif n_samples < 100:
        risks.append({
            "risk": "Small Sample Instability",
            "severity": "HIGH",
            "probability": 0.75,
            "impact": "High model variance. Cross-validation scores will be unreliable.",
            "mitigation": "Use LOO-CV or stratified k-fold. Apply strong regularization (Ridge/Lasso).",
            "affected_stage": "Training"
        })

    # 2. Descriptor explosion (curse of dimensionality)
    if ratio < 3.0:
        risks.append({
            "risk": "Descriptor Explosion",
            "severity": "HIGH",
            "probability": 0.85,
            "impact": f"N/P ratio is {ratio:.1f}. Model will overfit trivially.",
            "mitigation": "Apply PCA pre-processing or descriptor selection (VIF filtering, variance threshold).",
            "affected_stage": "Feature Engineering"
        })
    elif ratio < 10.0:
        risks.append({
            "risk": "High Dimensionality",
            "severity": "MEDIUM",
            "probability": 0.55,
            "impact": f"N/P ratio is {ratio:.1f}. Regularization is mandatory.",
            "mitigation": "Use ElasticNet, Ridge, or tree-based models with max_features constraint.",
            "affected_stage": "Feature Engineering"
        })

    # 3. Class imbalance
    breakdown = readiness_result.get("breakdown", {})
    class_balance_score = breakdown.get("class_balance", 100.0)
    if class_balance_score < 40:
        risks.append({
            "risk": "Severe Class Imbalance",
            "severity": "HIGH",
            "probability": 0.80,
            "impact": "Model will predict majority class only. Minority class recall ≈ 0.",
            "mitigation": "Apply SMOTE oversampling, class_weight='balanced', or ADASYN.",
            "affected_stage": "Training"
        })
    elif class_balance_score < 70:
        risks.append({
            "risk": "Moderate Class Imbalance",
            "severity": "MEDIUM",
            "probability": 0.50,
            "impact": "Biased predictions toward majority class.",
            "mitigation": "Use stratified cross-validation. Set class_weight='balanced'.",
            "affected_stage": "Training"
        })

    # 4. Scaffold leakage (data leakage risk)
    scaffold_level = diversity_result.get("scaffold_imbalance_level", "")
    if "High" in scaffold_level:
        risks.append({
            "risk": "Data Leakage (Scaffold Bias)",
            "severity": "HIGH",
            "probability": 0.80,
            "impact": "Random train/test split will leak structural information. CV scores will be overoptimistic.",
            "mitigation": "Use scaffold-split cross-validation (ScaffoldSplitter from DeepChem or custom Bemis-Murcko split).",
            "affected_stage": "Validation"
        })
    elif "Moderate" in scaffold_level:
        risks.append({
            "risk": "Moderate Scaffold Clustering",
            "severity": "MEDIUM",
            "probability": 0.45,
            "impact": "Some structural leakage possible with random splits.",
            "mitigation": "Consider scaffold-aware splitting for external validation sets.",
            "affected_stage": "Validation"
        })

    # 5. Descriptor reliability
    hard_excl = len(descriptor_result.get("hard_exclusion", []))
    rec_prune = len(descriptor_result.get("recommend_pruning", []))
    if hard_excl > 0:
        risks.append({
            "risk": "Unreliable Descriptors",
            "severity": "HIGH",
            "probability": 0.90,
            "impact": f"{hard_excl} descriptors have >70% missing values and will introduce noise.",
            "mitigation": "Drop hard_exclusion descriptors before any modeling step.",
            "affected_stage": "Feature Engineering"
        })
    if rec_prune > 5:
        risks.append({
            "risk": "Sparse Descriptor Coverage",
            "severity": "MEDIUM",
            "probability": 0.60,
            "impact": f"{rec_prune} descriptors have 40–70% missingness. Imputation will bias results.",
            "mitigation": "Apply median imputation or remove sparse descriptors. Consider indicator variables.",
            "affected_stage": "Feature Engineering"
        })

    # 6. Low predictive signal
    baseline_conf = success_result.get("confidence", "")
    if "Low" in baseline_conf:
        risks.append({
            "risk": "Low Predictive Signal",
            "severity": "HIGH",
            "probability": 0.75,
            "impact": "Baseline linear model shows near-zero R² / accuracy. SAR signal may be absent.",
            "mitigation": "Review endpoint quality. Check for measurement noise or mixed assay conditions.",
            "affected_stage": "Modeling"
        })

    # 7. Missing values
    miss_pct = health_metrics.get("missingness", {}).get("overall_missing_pct", 0)
    if miss_pct > 20:
        risks.append({
            "risk": "High Missing Value Density",
            "severity": "MEDIUM",
            "probability": 0.70,
            "impact": f"{miss_pct:.1f}% average missingness. Imputation will distort descriptor distributions.",
            "mitigation": "Run API enrichment to fill gaps. Use MICE or KNN imputation for numeric descriptors.",
            "affected_stage": "Preprocessing"
        })

    # Sort: CRITICAL first, then HIGH, MEDIUM, LOW
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    risks.sort(key=lambda r: order.get(r["severity"], 4))
    return risks

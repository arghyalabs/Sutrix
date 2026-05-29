"""
Model Recommender — rule-based algorithm suggestion engine.
Inputs: dataset characteristics. Does NOT train or evaluate models.
"""
from typing import Dict, Any, List


_MODELS = [
    {
        "algorithm": "Random Forest",
        "category": "Ensemble",
        "min_n": 80,
        "max_p_ratio": None,
        "handles_imbalance": True,
        "handles_regression": True,
        "handles_classification": True,
        "pros": [
            "Robust to outliers and noise",
            "Built-in feature importance (Gini impurity)",
            "Handles mixed descriptor scales without standardization",
            "No assumption of linearity"
        ],
        "cons": [
            "Memory-intensive for large feature sets",
            "Black-box: limited mechanistic interpretation",
            "Can overfit with very deep trees on small N"
        ],
        "scientific_reasoning": "Well-suited for QSAR datasets with mixed 2D/3D descriptors, moderate sample sizes, and non-linear SAR relationships. Industry standard for ecotoxicology endpoints.",
    },
    {
        "algorithm": "XGBoost",
        "category": "Gradient Boosting",
        "min_n": 150,
        "max_p_ratio": None,
        "handles_imbalance": True,
        "handles_regression": True,
        "handles_classification": True,
        "pros": [
            "State-of-the-art performance on tabular data",
            "scale_pos_weight handles class imbalance natively",
            "Built-in L1/L2 regularization",
            "Fast on CPU with parallel tree building"
        ],
        "cons": [
            "Many hyperparameters to tune",
            "Prone to overfitting without careful regularization",
            "Requires larger N than Random Forest"
        ],
        "scientific_reasoning": "Excellent for QSAR regression (LogP, pKa, LC50). Outperforms RF on large enriched descriptor sets. Preferred for publication-grade models.",
    },
    {
        "algorithm": "Support Vector Machine",
        "category": "Kernel Method",
        "min_n": 20,
        "max_n": 5000,
        "handles_imbalance": True,
        "handles_regression": True,
        "handles_classification": True,
        "pros": [
            "Effective in high-dimensional spaces (p >> n)",
            "Kernel trick captures non-linear relationships",
            "Memory efficient: only support vectors matter",
            "Well-established in cheminformatics literature"
        ],
        "cons": [
            "Scales poorly beyond 5,000 compounds",
            "Requires feature scaling",
            "Difficult to interpret mechanistically"
        ],
        "scientific_reasoning": "Classical QSAR workhorse. Particularly effective with RBF kernel on fingerprint-derived descriptors. Best choice for small-to-medium datasets with high-dimensional features.",
    },
    {
        "algorithm": "Ridge Regression",
        "category": "Linear Model",
        "min_n": 30,
        "handles_imbalance": False,
        "handles_regression": True,
        "handles_classification": False,
        "pros": [
            "Fully interpretable coefficient weights",
            "Fast training and prediction",
            "L2 regularization prevents overfitting on small N",
            "OECD-compliant transparent model"
        ],
        "cons": [
            "Assumes linearity in descriptor space",
            "Poor on non-linear SAR landscapes",
            "Cannot capture interaction terms without manual engineering"
        ],
        "scientific_reasoning": "OECD principle 2 compliant — unambiguous algorithm. Ideal as a baseline model and for mechanistic interpretation of linear SAR trends.",
    },
    {
        "algorithm": "LightGBM",
        "category": "Gradient Boosting",
        "min_n": 300,
        "handles_imbalance": True,
        "handles_regression": True,
        "handles_classification": True,
        "pros": [
            "10–100x faster than XGBoost on large datasets",
            "Leaf-wise tree growth captures complex patterns",
            "Excellent on high-cardinality descriptor matrices",
            "is_unbalance parameter for imbalanced datasets"
        ],
        "cons": [
            "Less reliable on very small datasets (<300 rows)",
            "Overfits easily without early stopping",
            "Requires careful n_estimators tuning"
        ],
        "scientific_reasoning": "Preferred for large-scale QSAR (>1000 compounds) with Mordred or full descriptor suites. Matches XGBoost accuracy at a fraction of the training time.",
    },
    {
        "algorithm": "PCA + K-Means",
        "category": "Unsupervised",
        "min_n": 20,
        "handles_imbalance": False,
        "handles_regression": False,
        "handles_classification": False,
        "unsupervised": True,
        "pros": [
            "No endpoint required — works on structural descriptors alone",
            "Reveals hidden chemical clusters",
            "Dimensionality reduction aids visualization",
            "OECD applicability domain analysis foundation"
        ],
        "cons": [
            "Does not predict biological endpoints",
            "Cluster count (k) must be chosen manually",
            "PCA variance explained may be low for diverse libraries"
        ],
        "scientific_reasoning": "Ideal for dataset profiling before endpoint modeling. Identifies chemical series, outlier compounds, and supports applicability domain definition (OECD principle 3).",
    },
]


def recommend_models(
    n_samples: int,
    n_features: int,
    endpoint_type: str,  # 'regression' | 'classification' | 'unknown'
    imbalance_score: float,  # 0-100 from readiness breakdown
    diversity_score: float,
) -> List[Dict[str, Any]]:
    """Returns scored + ranked model recommendations for this dataset."""
    results = []
    ratio = n_samples / max(1, n_features)
    is_classification = endpoint_type == "classification"
    is_regression = endpoint_type == "regression"
    severe_imbalance = imbalance_score < 40

    for m in _MODELS:
        if n_samples < m.get("min_n", 0):
            continue
        if m.get("max_n") and n_samples > m["max_n"]:
            continue
        if is_regression and not m.get("handles_regression", False) and not m.get("unsupervised", False):
            continue
        if is_classification and not m.get("handles_classification", False) and not m.get("unsupervised", False):
            continue

        # Compute suitability score 0-100
        score = 60  # baseline

        # Sample size bonus
        if n_samples >= 500:
            score += 15
        elif n_samples >= 200:
            score += 8

        # Imbalance handling
        if severe_imbalance and m.get("handles_imbalance"):
            score += 10
        elif severe_imbalance and not m.get("handles_imbalance"):
            score -= 15

        # Dimensionality
        if ratio < 3 and m["algorithm"] in ("Ridge Regression", "Support Vector Machine"):
            score += 10
        if ratio < 3 and m["algorithm"] in ("XGBoost", "LightGBM"):
            score -= 10

        # Chemical diversity bonus for ensemble methods
        if diversity_score > 0.5 and m["category"] == "Ensemble":
            score += 5

        # Interpretability bonus for linear on small N
        if n_samples < 100 and m["algorithm"] == "Ridge Regression":
            score += 15

        score = max(0, min(100, score))

        robustness = "HIGH" if score >= 75 else "MEDIUM" if score >= 50 else "LOW"

        results.append({
            "algorithm": m["algorithm"],
            "category": m["category"],
            "suitability_score": score,
            "pros": m["pros"],
            "cons": m["cons"],
            "expected_robustness": robustness,
            "scientific_reasoning": m["scientific_reasoning"],
            "unsupervised": m.get("unsupervised", False),
        })

    results.sort(key=lambda r: r["suitability_score"], reverse=True)
    return results

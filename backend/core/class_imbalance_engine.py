"""
Class Imbalance Engine — endpoint distribution and imbalance scoring.
Auto-detects classification vs regression targets.
All outputs are JSON-serializable.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


class ClassImbalanceEngine:
    """Analyzes target column for class imbalance (classification) or skewness (regression)."""

    @staticmethod
    def analyze(df: pd.DataFrame, target_col: str) -> Dict[str, Any]:
        """
        Analyzes the target column for class imbalance.

        Returns a unified dict covering both classification and regression targets.
        """
        if target_col not in df.columns:
            return {
                "error": f"Target column '{target_col}' not found",
                "is_continuous": True,
                "class_distribution": {},
                "class_percentages": {},
                "minority_class": None,
                "minority_ratio": None,
                "imbalance_score": 100.0,
                "shannon_entropy": 1.0,
                "gini_coefficient": 0.0,
                "n_classes": 0,
                "recommendations": [],
                "continuous_stats": None,
            }

        series = df[target_col].dropna()
        if len(series) == 0:
            return {
                "error": "Target column is empty",
                "is_continuous": True,
                "class_distribution": {},
                "class_percentages": {},
                "minority_class": None,
                "minority_ratio": None,
                "imbalance_score": 100.0,
                "shannon_entropy": 1.0,
                "gini_coefficient": 0.0,
                "n_classes": 0,
                "recommendations": [],
                "continuous_stats": None,
            }

        # Auto-detect classification vs regression
        dtype_is_numeric = pd.api.types.is_numeric_dtype(series)
        n_unique = series.nunique()
        is_continuous = dtype_is_numeric and n_unique > 10

        if is_continuous:
            # Regression path
            numeric = pd.to_numeric(series, errors="coerce").dropna()
            skew_val = float(numeric.skew()) if len(numeric) > 3 else 0.0
            kurt_val = float(numeric.kurtosis()) if len(numeric) > 3 else 0.0
            q25, q50, q75 = float(numeric.quantile(0.25)), float(numeric.median()), float(numeric.quantile(0.75))
            return {
                "is_continuous": True,
                "class_distribution": {},
                "class_percentages": {},
                "minority_class": None,
                "minority_ratio": None,
                "imbalance_score": 100.0,
                "shannon_entropy": 1.0,
                "gini_coefficient": 0.0,
                "n_classes": int(n_unique),
                "recommendations": [],
                "continuous_stats": {
                    "mean": round(float(numeric.mean()), 4),
                    "std": round(float(numeric.std()), 4),
                    "skew": round(skew_val, 4),
                    "kurt": round(kurt_val, 4),
                    "q25": round(q25, 4),
                    "q50": round(q50, 4),
                    "q75": round(q75, 4),
                    "min": round(float(numeric.min()), 4),
                    "max": round(float(numeric.max()), 4),
                    "n": int(len(numeric)),
                },
            }

        # Classification path
        counts = series.astype(str).value_counts()
        total = int(counts.sum())
        class_dist = {str(k): int(v) for k, v in counts.items()}
        class_pct = {str(k): round(float(v) / total * 100, 2) for k, v in counts.items()}

        minority_class = str(counts.index[-1])
        majority_class = str(counts.index[0])
        minority_count = int(counts.iloc[-1])
        majority_count = int(counts.iloc[0])
        minority_ratio = round(float(minority_count) / total, 4)

        # Shannon entropy (normalized)
        probs = counts.values / total
        entropy_raw = float(-np.sum(probs * np.log2(probs + 1e-12)))
        max_entropy = np.log2(len(counts)) if len(counts) > 1 else 1.0
        shannon_entropy = round(float(entropy_raw / max_entropy), 4)

        # Gini coefficient
        sorted_probs = np.sort(probs)
        n = len(sorted_probs)
        gini = float(1 - np.sum(sorted_probs ** 2)) if n > 0 else 0.0

        # Imbalance score: 0 = perfectly imbalanced, 100 = perfectly balanced
        # Based on how far minority_ratio is from 1/n_classes
        perfect_ratio = 1.0 / len(counts) if len(counts) > 0 else 1.0
        imbalance_score = round(max(0.0, min(100.0, (minority_ratio / perfect_ratio) * 100.0)), 2)

        # Recommendations
        recommendations = ClassImbalanceEngine._recommend(minority_ratio, len(counts))

        return {
            "is_continuous": False,
            "class_distribution": class_dist,
            "class_percentages": class_pct,
            "minority_class": minority_class,
            "majority_class": majority_class,
            "minority_ratio": minority_ratio,
            "majority_count": majority_count,
            "minority_count": minority_count,
            "imbalance_score": imbalance_score,
            "shannon_entropy": shannon_entropy,
            "gini_coefficient": round(gini, 4),
            "n_classes": int(len(counts)),
            "total_samples": total,
            "recommendations": recommendations,
            "continuous_stats": None,
        }

    @staticmethod
    def _recommend(minority_ratio: float, n_classes: int) -> List[Dict]:
        """Generates imbalance correction recommendations based on minority ratio."""
        recs = []
        if minority_ratio < 0.05:
            recs.append({
                "strategy": "SMOTE Oversampling",
                "severity": "CRITICAL",
                "reason": f"Minority class is only {minority_ratio*100:.1f}% of data — severe imbalance. "
                          "SMOTE generates synthetic minority-class samples.",
                "code_hint": (
                    "from imblearn.over_sampling import SMOTE\n"
                    "sm = SMOTE(random_state=42)\n"
                    "X_res, y_res = sm.fit_resample(X, y)"
                ),
            })
            recs.append({
                "strategy": "class_weight='balanced'",
                "severity": "CRITICAL",
                "reason": "Apply inverse-frequency class weights to penalize misclassification of the minority class.",
                "code_hint": "model = RandomForestClassifier(class_weight='balanced')",
            })
        elif minority_ratio < 0.20:
            recs.append({
                "strategy": "class_weight='balanced'",
                "severity": "HIGH",
                "reason": f"Minority class represents {minority_ratio*100:.1f}% — moderate imbalance. "
                          "Class weighting is the safest first intervention.",
                "code_hint": "model = LogisticRegression(class_weight='balanced')",
            })
            recs.append({
                "strategy": "SMOTEENN (Combined Sampling)",
                "severity": "HIGH",
                "reason": "Combines oversampling (SMOTE) with undersampling (ENN) for cleaner decision boundaries.",
                "code_hint": (
                    "from imblearn.combine import SMOTEENN\n"
                    "se = SMOTEENN(random_state=42)\n"
                    "X_res, y_res = se.fit_resample(X, y)"
                ),
            })
        elif minority_ratio < 0.40:
            recs.append({
                "strategy": "class_weight='balanced'",
                "severity": "MEDIUM",
                "reason": f"Minority class is {minority_ratio*100:.1f}%. Mild imbalance — class weighting may be sufficient.",
                "code_hint": "model = SVC(class_weight='balanced')",
            })
        # No recommendation if perfectly balanced

        return recs

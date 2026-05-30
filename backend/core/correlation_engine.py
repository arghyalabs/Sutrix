"""
Correlation Engine - Pearson + Spearman + redundancy detection.
All outputs must be JSON-serializable.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

try:
    from scipy import stats as scipy_stats
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

logger = logging.getLogger("sdo.core.correlation_engine")


class CorrelationEngine:
    """
    Computes Pearson and Spearman correlation matrices, identifies highly correlated
    feature pairs, and produces redundancy reports for feature selection.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _select_features(df: pd.DataFrame, descriptor_cols: List[str], max_features: int) -> List[str]:
        """Return up to max_features descriptor columns ranked by variance (descending)."""
        available = [c for c in descriptor_cols if c in df.columns]
        if not available:
            return []
        numeric = df[available].apply(pd.to_numeric, errors="coerce")
        variances = numeric.var(ddof=0)
        variances = variances.dropna().sort_values(ascending=False)
        return list(variances.index[:max_features])

    @staticmethod
    def _matrix_to_lists(matrix: np.ndarray) -> List[List[float]]:
        """Convert 2D numpy matrix to nested list of plain Python floats."""
        return [[round(float(v), 6) for v in row] for row in matrix]

    # ------------------------------------------------------------------
    # Pearson
    # ------------------------------------------------------------------

    @staticmethod
    def compute_pearson(
        df: pd.DataFrame,
        descriptor_cols: List[str],
        max_features: int = 50,
    ) -> Dict:
        """
        Compute Pearson correlation matrix.
        Returns {"z": [[...]], "labels": [...]}
        """
        if df is None or df.empty or not descriptor_cols:
            return {"z": [], "labels": []}

        cols = CorrelationEngine._select_features(df, descriptor_cols, max_features)
        if not cols:
            return {"z": [], "labels": []}

        try:
            sub = df[cols].apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
            sub = sub.fillna(sub.median())
            if sub.shape[1] < 2:
                return {"z": [], "labels": []}
            corr_matrix = sub.corr(method="pearson").values
            return {
                "z": CorrelationEngine._matrix_to_lists(corr_matrix),
                "labels": list(sub.columns),
            }
        except Exception as exc:
            logger.error("Pearson computation failed: %s", exc)
            return {"z": [], "labels": []}

    # ------------------------------------------------------------------
    # Spearman
    # ------------------------------------------------------------------

    @staticmethod
    def compute_spearman(
        df: pd.DataFrame,
        descriptor_cols: List[str],
        max_features: int = 50,
    ) -> Dict:
        """
        Compute Spearman correlation matrix.
        Returns {"z": [[...]], "labels": [...]}
        """
        if df is None or df.empty or not descriptor_cols:
            return {"z": [], "labels": []}

        cols = CorrelationEngine._select_features(df, descriptor_cols, max_features)
        if not cols:
            return {"z": [], "labels": []}

        try:
            sub = df[cols].apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
            sub = sub.fillna(sub.median())
            if sub.shape[1] < 2:
                return {"z": [], "labels": []}

            if _HAS_SCIPY:
                corr_matrix, _ = scipy_stats.spearmanr(sub.values)
                if corr_matrix.ndim == 0:
                    # Only 2 columns case
                    corr_matrix = np.array([[1.0, float(corr_matrix)], [float(corr_matrix), 1.0]])
            else:
                corr_matrix = sub.corr(method="spearman").values

            return {
                "z": CorrelationEngine._matrix_to_lists(corr_matrix),
                "labels": list(sub.columns),
            }
        except Exception as exc:
            logger.error("Spearman computation failed: %s", exc)
            return {"z": [], "labels": []}

    # ------------------------------------------------------------------
    # High-correlation pairs
    # ------------------------------------------------------------------

    @staticmethod
    def find_high_correlation_pairs(
        pearson_z: List[List[float]],
        labels: List[str],
        thresholds: List[float] = None,
    ) -> List[Dict]:
        """
        Scan upper triangle of the Pearson matrix for pairs exceeding any threshold.
        Returns list of {feat1, feat2, pearson_r, threshold_exceeded, recommendation}.
        """
        if thresholds is None:
            thresholds = [0.85, 0.90, 0.95]

        if not pearson_z or not labels:
            return []

        pairs: List[Dict] = []
        n = len(labels)
        mat = np.array(pearson_z, dtype=float)

        for i in range(n):
            for j in range(i + 1, n):
                r = float(mat[i, j])
                abs_r = abs(r)
                exceeded = [t for t in thresholds if abs_r >= t]
                if not exceeded:
                    continue
                max_t = max(exceeded)
                if max_t >= 0.95:
                    recommendation = f"DROP '{labels[j]}' — near-perfect correlation ({r:.3f}) with '{labels[i]}'"
                elif max_t >= 0.90:
                    recommendation = f"REVIEW '{labels[j]}' — very high correlation ({r:.3f}) with '{labels[i]}'"
                else:
                    recommendation = f"CONSIDER removing '{labels[j]}' — high correlation ({r:.3f}) with '{labels[i]}'"

                pairs.append({
                    "feat1": labels[i],
                    "feat2": labels[j],
                    "pearson_r": round(r, 6),
                    "threshold_exceeded": round(max_t, 2),
                    "recommendation": recommendation,
                })

        return pairs

    # ------------------------------------------------------------------
    # Redundancy report
    # ------------------------------------------------------------------

    @staticmethod
    def build_redundancy_report(pairs: List[Dict]) -> Dict:
        """
        Summarise pairs into a redundancy report and produce recommended drops.
        A feature is recommended for drop if it appears as feat2 in a >= 0.95 pair.
        """
        if not pairs:
            return {
                "total_redundant_pairs": 0,
                "by_threshold": {},
                "most_connected": [],
            }

        from collections import Counter
        threshold_counts: Dict[float, int] = {}
        feat2_counter: Counter = Counter()

        for p in pairs:
            t = p["threshold_exceeded"]
            threshold_counts[t] = threshold_counts.get(t, 0) + 1
            if t >= 0.95:
                feat2_counter[p["feat2"]] += 1

        most_connected = [
            {"feature": f, "n_high_corr_partners": c}
            for f, c in feat2_counter.most_common(20)
        ]

        return {
            "total_redundant_pairs": len(pairs),
            "by_threshold": {str(k): v for k, v in threshold_counts.items()},
            "most_connected": most_connected,
        }

    # ------------------------------------------------------------------
    # Full analysis
    # ------------------------------------------------------------------

    @classmethod
    def run_full_analysis(
        cls,
        df: pd.DataFrame,
        descriptor_cols: List[str],
        max_features: int = 50,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Run Pearson + Spearman + redundancy analysis.
        Returns JSON-serializable result dict.
        """

        def _cb(pct: int, phase: str):
            if progress_callback is not None:
                try:
                    progress_callback(pct, phase)
                except Exception:
                    pass

        if df is None or df.empty or not descriptor_cols:
            return {
                "pearson": {"z": [], "labels": []},
                "spearman": {"z": [], "labels": []},
                "high_correlation_pairs": [],
                "redundancy_count": 0,
                "recommended_drops": [],
            }

        _cb(10, "Computing Pearson correlation")
        pearson = cls.compute_pearson(df, descriptor_cols, max_features=max_features)

        _cb(35, "Computing Spearman correlation")
        spearman = cls.compute_spearman(df, descriptor_cols, max_features=max_features)

        _cb(60, "Finding high-correlation pairs")
        pairs = cls.find_high_correlation_pairs(
            pearson["z"], pearson["labels"], thresholds=[0.85, 0.90, 0.95]
        )

        _cb(80, "Building redundancy report")
        report = cls.build_redundancy_report(pairs)

        # Recommended drops: feat2 in any pair with threshold >= 0.95
        recommended_drops = list({
            p["feat2"] for p in pairs if p["threshold_exceeded"] >= 0.95
        })

        _cb(100, "Complete")

        return {
            "pearson": pearson,
            "spearman": spearman,
            "high_correlation_pairs": pairs,
            "redundancy_count": int(len(pairs)),
            "recommended_drops": recommended_drops,
            "redundancy_report": report,
        }

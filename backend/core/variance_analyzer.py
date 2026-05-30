"""
Variance Threshold Analyzer - detects near-constant and low-variance features.
All outputs must be JSON-serializable.
"""
import logging
import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger("sdo.core.variance_analyzer")


class VarianceThresholdAnalyzer:
    """
    Analyzes descriptor variance to identify near-zero-variance (NZV) and
    low-variance features that add noise without signal.
    """

    @staticmethod
    def analyze(
        df: pd.DataFrame,
        descriptor_cols: List[str],
        threshold: float = 0.01,
    ) -> Dict[str, Any]:
        """
        Compute per-feature variance, classify features, and build histogram data.

        Parameters
        ----------
        df : pd.DataFrame
            Dataset containing descriptors.
        descriptor_cols : list[str]
            Column names for descriptor features.
        threshold : float
            Variance below this → DROP. Below threshold*10 → REVIEW.

        Returns
        -------
        dict with keys: features, near_zero_count, low_variance_count,
                        safe_count, total_features, variance_histogram, threshold_used
        """
        if df is None or df.empty or not descriptor_cols:
            return {
                "features": [],
                "near_zero_count": 0,
                "low_variance_count": 0,
                "safe_count": 0,
                "total_features": 0,
                "variance_histogram": {"log_values": [], "bins": [], "counts": []},
                "threshold_used": float(threshold),
            }

        available = [c for c in descriptor_cols if c in df.columns]
        if not available:
            return {
                "features": [],
                "near_zero_count": 0,
                "low_variance_count": 0,
                "safe_count": 0,
                "total_features": 0,
                "variance_histogram": {"log_values": [], "bins": [], "counts": []},
                "threshold_used": float(threshold),
            }

        sub = df[available].apply(pd.to_numeric, errors="coerce")
        variances = sub.var(ddof=0)

        features: List[Dict[str, Any]] = []
        near_zero_count = 0
        low_variance_count = 0
        safe_count = 0

        low_threshold = threshold * 10.0

        log_values: List[float] = []

        for col in available:
            v = variances.get(col, 0.0)
            if pd.isna(v):
                v = 0.0
            v = float(v)

            # log variance for histogram (handle 0 / negatives gracefully)
            if v > 0:
                log_v = float(math.log10(v))
            else:
                log_v = float(-10)  # sentinel for zero variance

            log_values.append(log_v)

            if v < threshold:
                status = "DROP"
                recommendation = (
                    f"'{col}' has near-zero variance ({v:.4g}). "
                    "This feature is essentially constant and should be removed."
                )
                near_zero_count += 1
            elif v < low_threshold:
                status = "REVIEW"
                recommendation = (
                    f"'{col}' has low variance ({v:.4g}). "
                    "Consider removing unless domain-relevant."
                )
                low_variance_count += 1
            else:
                status = "KEEP"
                recommendation = f"'{col}' has sufficient variance ({v:.4g})."
                safe_count += 1

            features.append({
                "feature": col,
                "variance": round(v, 8),
                "log_variance": round(log_v, 4),
                "status": status,
                "recommendation": recommendation,
            })

        # Build histogram of log-variance values
        histogram: Dict[str, Any] = {"log_values": [], "bins": [], "counts": []}
        if log_values:
            try:
                counts_arr, bin_edges = np.histogram(log_values, bins=30)
                histogram = {
                    "log_values": [round(float(v), 4) for v in log_values],
                    "bins": [round(float(b), 4) for b in bin_edges.tolist()],
                    "counts": [int(c) for c in counts_arr.tolist()],
                }
            except Exception as exc:
                logger.warning("Histogram computation failed: %s", exc)

        return {
            "features": features,
            "near_zero_count": int(near_zero_count),
            "low_variance_count": int(low_variance_count),
            "safe_count": int(safe_count),
            "total_features": int(len(available)),
            "variance_histogram": histogram,
            "threshold_used": float(threshold),
        }

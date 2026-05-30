"""
Applicability Domain Engine - Williams plot, leverage analysis, distance-based domain.
All outputs must be JSON-serializable.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

logger = logging.getLogger("sdo.core.applicability_domain_engine")

_MAX_LEVERAGE_ROWS = 5_000
_MAX_WILLIAMS_POINTS = 2_000
_MAX_FEATURES = 50


class ApplicabilityDomainEngine:
    """
    Computes leverage-based applicability domain and produces Williams plot data.
    """

    # ------------------------------------------------------------------
    # Core computations
    # ------------------------------------------------------------------

    @staticmethod
    def compute_leverage(X: np.ndarray) -> np.ndarray:
        """
        Compute hat matrix diagonal h_i = x_i^T (X^T X)^{-1} x_i.
        Uses pseudoinverse for numerical stability.
        """
        if X is None or X.size == 0:
            return np.array([])
        try:
            # hat = X (X^T X)^-1 X^T → diagonal only
            XtX_inv = np.linalg.pinv(X.T @ X)
            # Compute diagonal efficiently: h_i = row_i @ XtX_inv @ row_i^T
            leverage = np.einsum("ij,jk,ik->i", X, XtX_inv, X)
            return leverage
        except Exception as exc:
            logger.error("Leverage computation failed: %s", exc)
            return np.zeros(X.shape[0])

    @staticmethod
    def compute_h_star(n_samples: int, n_features: int) -> float:
        """
        Critical leverage threshold: h* = 3 * (p + 1) / n
        """
        if n_samples <= 0:
            return 0.0
        return float(3 * (n_features + 1) / max(n_samples, 1))

    @staticmethod
    def classify_domain(
        leverage: np.ndarray,
        h_star: float,
        std_residuals: Optional[np.ndarray] = None,
        residual_threshold: float = 3.0,
    ) -> np.ndarray:
        """
        Classify each compound as 'INSIDE', 'BORDERLINE', or 'OUTSIDE'.

        A compound is OUTSIDE if leverage > h_star OR |std_residual| > threshold.
        BORDERLINE if leverage is within [0.8*h_star, h_star] (inside leverage, high residual).
        """
        if leverage is None or len(leverage) == 0:
            return np.array([], dtype=object)

        n = len(leverage)
        if std_residuals is None or len(std_residuals) != n:
            std_residuals = np.zeros(n)

        classifications = np.full(n, "INSIDE", dtype=object)

        high_leverage = leverage > h_star
        borderline_leverage = (leverage > 0.8 * h_star) & ~high_leverage
        high_residual = np.abs(std_residuals) > residual_threshold

        # OUTSIDE: high leverage OR high residual
        outside_mask = high_leverage | (high_residual & ~borderline_leverage)
        classifications[outside_mask] = "OUTSIDE"

        # BORDERLINE: near leverage boundary with moderate residual
        borderline_mask = borderline_leverage & ~outside_mask
        classifications[borderline_mask] = "BORDERLINE"

        return classifications

    # ------------------------------------------------------------------
    # Full analysis
    # ------------------------------------------------------------------

    @classmethod
    def run_full_analysis(
        cls,
        df: pd.DataFrame,
        descriptor_cols: List[str],
        target_col: Optional[str] = None,
        smiles_col: Optional[str] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        End-to-end applicability domain analysis.
        Returns a JSON-serializable result dict.
        """

        def _cb(pct: int, phase: str):
            if progress_callback is not None:
                try:
                    progress_callback(pct, phase)
                except Exception:
                    pass

        empty = {
            "leverage_values": [],
            "h_star": 0.0,
            "domain_classification": [],
            "inside_count": 0,
            "borderline_count": 0,
            "outside_count": 0,
            "inside_pct": 0.0,
            "williams_plot_data": {
                "leverage": [], "std_residuals": [], "domain": [], "smiles": []
            },
            "distance_distribution": {"values": [], "bins": [], "counts": []},
            "n_outside_domain": 0,
            "domain_coverage_pct": 0.0,
        }

        if df is None or df.empty or not descriptor_cols:
            return empty

        if not _HAS_SKLEARN:
            logger.error("sklearn is required for ApplicabilityDomainEngine")
            return empty

        _cb(10, "Preparing descriptor matrix")
        available = [c for c in descriptor_cols if c in df.columns]
        if not available:
            return empty

        sub = df[available].apply(pd.to_numeric, errors="coerce")

        # Select top _MAX_FEATURES by variance
        variances = sub.var(ddof=0).fillna(0)
        top_cols = variances.nlargest(_MAX_FEATURES).index.tolist()
        sub = sub[top_cols]

        _cb(25, "Imputing missing values")
        imputer = SimpleImputer(strategy="median")
        X_imp = imputer.fit_transform(sub.values)

        _cb(40, "Scaling features")
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_imp)

        n_samples, n_features = X_scaled.shape

        # Subsample for leverage if dataset is large
        use_subsample = n_samples > _MAX_LEVERAGE_ROWS
        if use_subsample:
            _cb(50, f"Subsampling to {_MAX_LEVERAGE_ROWS} rows for leverage")
            rng = np.random.default_rng(42)
            idx = rng.choice(n_samples, _MAX_LEVERAGE_ROWS, replace=False)
            X_lev = X_scaled[idx]
        else:
            X_lev = X_scaled

        _cb(60, "Computing leverage values")
        leverage = cls.compute_leverage(X_scaled)
        h_star = cls.compute_h_star(X_lev.shape[0], n_features)

        # Build std_residuals
        _cb(70, "Computing standardised residuals")
        if target_col and target_col in df.columns:
            y = pd.to_numeric(df[target_col], errors="coerce").fillna(0).values
            y_mean = y.mean()
            y_std = y.std()
            if y_std > 1e-10:
                std_residuals = (y - y_mean) / y_std
            else:
                std_residuals = np.zeros(n_samples)
        else:
            std_residuals = np.zeros(n_samples)

        _cb(80, "Classifying domain membership")
        domain_class = cls.classify_domain(leverage, h_star, std_residuals)

        inside_count = int(np.sum(domain_class == "INSIDE"))
        borderline_count = int(np.sum(domain_class == "BORDERLINE"))
        outside_count = int(np.sum(domain_class == "OUTSIDE"))
        total = n_samples
        inside_pct = round(float(inside_count + borderline_count) / max(total, 1) * 100, 2)
        domain_coverage_pct = inside_pct

        # SMILES list
        if smiles_col and smiles_col in df.columns:
            smiles_list = df[smiles_col].fillna("").astype(str).tolist()
        else:
            smiles_list = [""] * n_samples

        # Williams plot data — sample up to _MAX_WILLIAMS_POINTS
        _cb(88, "Building Williams plot data")
        if n_samples > _MAX_WILLIAMS_POINTS:
            rng2 = np.random.default_rng(99)
            wp_idx = rng2.choice(n_samples, _MAX_WILLIAMS_POINTS, replace=False)
        else:
            wp_idx = np.arange(n_samples)

        williams_plot_data = {
            "leverage": [round(float(leverage[i]), 6) for i in wp_idx],
            "std_residuals": [round(float(std_residuals[i]), 6) for i in wp_idx],
            "domain": [str(domain_class[i]) for i in wp_idx],
            "smiles": [smiles_list[i] for i in wp_idx],
        }

        # Distance distribution (leverage as proxy)
        _cb(93, "Building distance distribution")
        distance_distribution: Dict[str, Any] = {"values": [], "bins": [], "counts": []}
        try:
            lev_vals = leverage.tolist()
            counts_arr, bin_edges = np.histogram(lev_vals, bins=30)
            distance_distribution = {
                "values": [round(float(v), 6) for v in lev_vals],
                "bins": [round(float(b), 6) for b in bin_edges.tolist()],
                "counts": [int(c) for c in counts_arr.tolist()],
            }
        except Exception as exc:
            logger.warning("Distance distribution histogram failed: %s", exc)

        _cb(100, "Complete")

        return {
            "leverage_values": [round(float(v), 6) for v in leverage.tolist()],
            "h_star": round(float(h_star), 6),
            "domain_classification": [str(d) for d in domain_class.tolist()],
            "inside_count": inside_count,
            "borderline_count": borderline_count,
            "outside_count": outside_count,
            "inside_pct": inside_pct,
            "williams_plot_data": williams_plot_data,
            "distance_distribution": distance_distribution,
            "n_outside_domain": outside_count,
            "domain_coverage_pct": domain_coverage_pct,
        }

"""
Outlier Intelligence Engine - multi-method outlier detection.
Combines IsolationForest, LOF, Z-score and IQR approaches into a unified risk score.
All outputs must be JSON-serializable.
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

try:
    from sklearn.ensemble import IsolationForest as _IsolationForest
    from sklearn.neighbors import LocalOutlierFactor as _LOF
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

logger = logging.getLogger("sdo.core.outlier_engine")

_MAX_EXPENSIVE_ROWS = 10_000
_MAX_FEATURES = 100


class OutlierEngine:
    """
    Multi-method outlier detection engine.  Each compound receives a risk_score
    (0.0-1.0) equal to the fraction of methods that flagged it.
    """

    # ------------------------------------------------------------------
    # Matrix preparation
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_matrix(df: pd.DataFrame, descriptor_cols: List[str]) -> np.ndarray:
        """
        Impute median, StandardScale, then keep top _MAX_FEATURES by variance.
        Returns float64 numpy array.
        """
        if not _HAS_SKLEARN:
            raise ImportError("sklearn is required for OutlierEngine")

        available = [c for c in descriptor_cols if c in df.columns]
        if not available:
            return np.empty((0, 0))

        sub = df[available].apply(pd.to_numeric, errors="coerce")

        # Keep top features by variance
        variances = sub.var(ddof=0).fillna(0)
        top_cols = variances.nlargest(_MAX_FEATURES).index.tolist()
        sub = sub[top_cols]

        imputer = SimpleImputer(strategy="median")
        X_imp = imputer.fit_transform(sub.values)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_imp)

        return X_scaled

    # ------------------------------------------------------------------
    # Method: Isolation Forest
    # ------------------------------------------------------------------

    @staticmethod
    def isolation_forest(X: np.ndarray, contamination: float = 0.05) -> np.ndarray:
        """
        Run IsolationForest. Returns +1 (inlier) / -1 (outlier) array.
        Limits input to _MAX_EXPENSIVE_ROWS rows.
        """
        if not _HAS_SKLEARN:
            return np.ones(X.shape[0], dtype=int)
        if X is None or X.size == 0:
            return np.array([], dtype=int)

        n = X.shape[0]
        work_X = X[:_MAX_EXPENSIVE_ROWS] if n > _MAX_EXPENSIVE_ROWS else X

        try:
            clf = _IsolationForest(
                contamination=float(contamination),
                random_state=42,
                n_jobs=-1,
            )
            preds_work = clf.fit_predict(work_X)

            if n > _MAX_EXPENSIVE_ROWS:
                # Remaining rows: use decision_function, threshold=0
                scores_rest = clf.decision_function(X[_MAX_EXPENSIVE_ROWS:])
                preds_rest = np.where(scores_rest >= 0, 1, -1)
                preds = np.concatenate([preds_work, preds_rest])
            else:
                preds = preds_work

            return preds.astype(int)
        except Exception as exc:
            logger.error("IsolationForest failed: %s", exc)
            return np.ones(n, dtype=int)

    # ------------------------------------------------------------------
    # Method: Local Outlier Factor
    # ------------------------------------------------------------------

    @staticmethod
    def local_outlier_factor(X: np.ndarray, n_neighbors: int = 20) -> np.ndarray:
        """
        Run LOF. Returns +1 (inlier) / -1 (outlier) label array.
        Limits input to _MAX_EXPENSIVE_ROWS rows.
        """
        if not _HAS_SKLEARN:
            return np.ones(X.shape[0], dtype=int)
        if X is None or X.size == 0:
            return np.array([], dtype=int)

        n = X.shape[0]
        work_X = X[:_MAX_EXPENSIVE_ROWS] if n > _MAX_EXPENSIVE_ROWS else X

        try:
            k = min(n_neighbors, work_X.shape[0] - 1)
            if k < 1:
                return np.ones(n, dtype=int)

            clf = _LOF(n_neighbors=k, novelty=False, n_jobs=-1)
            preds_work = clf.fit_predict(work_X)

            if n > _MAX_EXPENSIVE_ROWS:
                # LOF without novelty=True cannot predict on unseen; mark remaining as inlier
                preds_rest = np.ones(n - _MAX_EXPENSIVE_ROWS, dtype=int)
                preds = np.concatenate([preds_work, preds_rest])
            else:
                preds = preds_work

            return preds.astype(int)
        except Exception as exc:
            logger.error("LOF failed: %s", exc)
            return np.ones(n, dtype=int)

    # ------------------------------------------------------------------
    # Method: Z-score
    # ------------------------------------------------------------------

    @staticmethod
    def zscore_outliers(
        df: pd.DataFrame,
        descriptor_cols: List[str],
        threshold: float = 3.0,
    ) -> np.ndarray:
        """
        Flag compounds where ANY descriptor has |z-score| > threshold.
        Returns boolean array (True = outlier).
        """
        available = [c for c in descriptor_cols if c in df.columns]
        if not available:
            return np.zeros(len(df), dtype=bool)

        sub = df[available].apply(pd.to_numeric, errors="coerce")
        sub_filled = sub.fillna(sub.median())

        means = sub_filled.mean(axis=0)
        stds = sub_filled.std(axis=0, ddof=0).replace(0, np.nan)
        z = ((sub_filled - means) / stds).abs()

        flagged = (z > threshold).any(axis=1).values
        return flagged.astype(bool)

    # ------------------------------------------------------------------
    # Method: IQR
    # ------------------------------------------------------------------

    @staticmethod
    def iqr_outliers(
        df: pd.DataFrame,
        descriptor_cols: List[str],
        multiplier: float = 1.5,
    ) -> np.ndarray:
        """
        Flag compounds outside [Q1 - multiplier*IQR, Q3 + multiplier*IQR]
        on ANY descriptor. Returns boolean array (True = outlier).
        """
        available = [c for c in descriptor_cols if c in df.columns]
        if not available:
            return np.zeros(len(df), dtype=bool)

        sub = df[available].apply(pd.to_numeric, errors="coerce")
        sub_filled = sub.fillna(sub.median())

        q1 = sub_filled.quantile(0.25)
        q3 = sub_filled.quantile(0.75)
        iqr = q3 - q1

        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr

        outside = ((sub_filled < lower) | (sub_filled > upper)).any(axis=1).values
        return outside.astype(bool)

    # ------------------------------------------------------------------
    # Full analysis
    # ------------------------------------------------------------------

    @classmethod
    def run_full_analysis(
        cls,
        df: pd.DataFrame,
        descriptor_cols: List[str],
        smiles_col: Optional[str] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Run all four outlier detection methods and aggregate risk scores.
        Returns JSON-serializable result dict.
        """

        def _cb(pct: int, phase: str):
            if progress_callback is not None:
                try:
                    progress_callback(pct, phase)
                except Exception:
                    pass

        empty = {
            "compound_risk_scores": [],
            "outlier_density_pct": 0.0,
            "high_risk_count": 0,
            "method_counts": {
                "IsolationForest": 0,
                "LOF": 0,
                "ZScore": 0,
                "IQR": 0,
            },
            "risk_distribution": {"bins": [], "counts": []},
            "n_samples": 0,
        }

        if df is None or df.empty or not descriptor_cols:
            return empty

        n_samples = len(df)
        _cb(10, "Preparing feature matrix")

        # ------ Prepare scaled matrix for sklearn methods ------
        try:
            X = cls._prepare_matrix(df, descriptor_cols)
            has_matrix = X is not None and X.size > 0
        except Exception as exc:
            logger.error("Matrix preparation failed: %s", exc)
            has_matrix = False
            X = np.empty((0, 0))

        _cb(25, "Running Isolation Forest")
        if has_matrix:
            if_preds = cls.isolation_forest(X, contamination=0.05)
            if_outlier = (if_preds == -1)
        else:
            if_outlier = np.zeros(n_samples, dtype=bool)

        _cb(45, "Running Local Outlier Factor")
        if has_matrix:
            lof_preds = cls.local_outlier_factor(X, n_neighbors=20)
            lof_outlier = (lof_preds == -1)
        else:
            lof_outlier = np.zeros(n_samples, dtype=bool)

        _cb(62, "Running Z-score analysis")
        try:
            zs_outlier = cls.zscore_outliers(df, descriptor_cols, threshold=3.0)
        except Exception as exc:
            logger.error("Z-score failed: %s", exc)
            zs_outlier = np.zeros(n_samples, dtype=bool)

        _cb(75, "Running IQR analysis")
        try:
            iqr_outlier = cls.iqr_outliers(df, descriptor_cols, multiplier=1.5)
        except Exception as exc:
            logger.error("IQR failed: %s", exc)
            iqr_outlier = np.zeros(n_samples, dtype=bool)

        _cb(85, "Computing risk scores")

        # Align array lengths (in case subsampling occurred)
        def _pad(arr: np.ndarray, target: int) -> np.ndarray:
            if len(arr) >= target:
                return arr[:target].astype(bool)
            padded = np.zeros(target, dtype=bool)
            padded[: len(arr)] = arr.astype(bool)
            return padded

        if_outlier = _pad(if_outlier, n_samples)
        lof_outlier = _pad(lof_outlier, n_samples)
        zs_outlier = _pad(zs_outlier, n_samples)
        iqr_outlier = _pad(iqr_outlier, n_samples)

        methods_arr = np.stack(
            [if_outlier, lof_outlier, zs_outlier, iqr_outlier], axis=1
        ).astype(float)  # shape (n_samples, 4)

        risk_scores = methods_arr.mean(axis=1)  # 0.0 to 1.0

        # SMILES
        if smiles_col and smiles_col in df.columns:
            smiles_list = df[smiles_col].fillna("").astype(str).tolist()
        else:
            smiles_list = [""] * n_samples

        # Build compound risk score records (only non-zero risk)
        _cb(92, "Building result table")
        compound_risk_scores: List[Dict[str, Any]] = []
        high_risk_count = 0

        for i in range(n_samples):
            rs = float(risk_scores[i])
            if rs <= 0.0:
                continue
            flagged_by: List[str] = []
            if bool(if_outlier[i]):
                flagged_by.append("IsolationForest")
            if bool(lof_outlier[i]):
                flagged_by.append("LOF")
            if bool(zs_outlier[i]):
                flagged_by.append("ZScore")
            if bool(iqr_outlier[i]):
                flagged_by.append("IQR")

            if rs >= 0.5:
                high_risk_count += 1

            compound_risk_scores.append({
                "index": int(i),
                "smiles": smiles_list[i],
                "risk_score": round(rs, 4),
                "flagged_by": flagged_by,
            })

        # Method-level counts
        method_counts = {
            "IsolationForest": int(if_outlier.sum()),
            "LOF": int(lof_outlier.sum()),
            "ZScore": int(zs_outlier.sum()),
            "IQR": int(iqr_outlier.sum()),
        }

        # Outlier density = fraction with risk_score > 0
        outlier_density_pct = round(
            float(len(compound_risk_scores)) / max(n_samples, 1) * 100.0, 2
        )

        # Risk score distribution histogram
        risk_distribution: Dict[str, Any] = {"bins": [], "counts": []}
        try:
            counts_arr, bin_edges = np.histogram(risk_scores, bins=10, range=(0.0, 1.0))
            risk_distribution = {
                "bins": [round(float(b), 3) for b in bin_edges.tolist()],
                "counts": [int(c) for c in counts_arr.tolist()],
            }
        except Exception as exc:
            logger.warning("Risk histogram failed: %s", exc)

        _cb(100, "Complete")

        return {
            "compound_risk_scores": compound_risk_scores,
            "outlier_density_pct": outlier_density_pct,
            "high_risk_count": int(high_risk_count),
            "method_counts": method_counts,
            "risk_distribution": risk_distribution,
            "n_samples": int(n_samples),
        }

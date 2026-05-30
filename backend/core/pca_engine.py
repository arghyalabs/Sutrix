"""
PCA Engine - Real sklearn PCA implementation.
Handles missing values, scaling, variance analysis, loadings, and outlier detection.
All result values must be JSON-serializable (no numpy types).
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

try:
    from sklearn.decomposition import PCA
except ImportError:
    PCA = None

try:
    from sklearn.preprocessing import StandardScaler
except ImportError:
    StandardScaler = None

try:
    from sklearn.impute import SimpleImputer
except ImportError:
    SimpleImputer = None

logger = logging.getLogger("sdo.core.pca_engine")


class PCAEngine:
    """
    Full PCA analysis engine backed by sklearn.
    Handles preprocessing, decomposition, variance analysis, loadings, and outlier detection.
    All outputs are JSON-serializable (plain Python floats/ints/bools, not numpy types).
    """

    def __init__(self, n_components: int = 10):
        self.n_components = n_components
        self._pca: Optional[Any] = None
        self._scaler: Optional[Any] = None
        self._imputer: Optional[Any] = None
        self._feature_names: List[str] = []
        self._n_features_dropped: int = 0

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def prepare_matrix(self, df: pd.DataFrame, descriptor_cols: List[str]) -> np.ndarray:
        """
        Select descriptor columns, drop >90% missing, impute median, return float array.
        Side-effects: sets self._feature_names, self._n_features_dropped.
        """
        if df is None or df.empty or not descriptor_cols:
            return np.empty((0, 0))

        available = [c for c in descriptor_cols if c in df.columns]
        if not available:
            return np.empty((0, 0))

        sub = df[available].copy()

        # Convert everything to numeric, coerce errors to NaN
        for col in sub.columns:
            sub[col] = pd.to_numeric(sub[col], errors="coerce")

        # Drop columns with >90% missing values
        missing_frac = sub.isna().mean()
        keep_mask = missing_frac <= 0.90
        dropped = int((~keep_mask).sum())
        self._n_features_dropped = dropped
        sub = sub.loc[:, keep_mask]

        if sub.empty or sub.shape[1] == 0:
            self._feature_names = []
            return np.empty((0, 0))

        self._feature_names = list(sub.columns)
        return sub.values.astype(float)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """
        Impute, scale, then PCA-transform X.
        Returns the PC projections array of shape (n_samples, n_components_used).
        """
        if X is None or X.size == 0 or X.shape[0] < 2:
            return np.empty((0, 0))

        if SimpleImputer is None or StandardScaler is None or PCA is None:
            raise ImportError("sklearn is required for PCAEngine.fit_transform")

        # Impute
        self._imputer = SimpleImputer(strategy="median")
        X_imp = self._imputer.fit_transform(X)

        # Scale
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X_imp)

        # Determine n_components
        n_comp = min(self.n_components, X_scaled.shape[0] - 1, X_scaled.shape[1])
        if n_comp < 1:
            return np.empty((0, 0))

        self._pca = PCA(n_components=n_comp)
        projections = self._pca.fit_transform(X_scaled)
        return projections

    # ------------------------------------------------------------------
    # Variance
    # ------------------------------------------------------------------

    def compute_variance_explained(self) -> List[Dict]:
        """Returns per-component variance explained as a list of dicts."""
        if self._pca is None:
            return []
        ratios = self._pca.explained_variance_ratio_
        result = []
        cumulative = 0.0
        for i, r in enumerate(ratios):
            cumulative += float(r) * 100.0
            result.append({
                "component": f"PC{i + 1}",
                "variance_pct": round(float(r) * 100.0, 4),
                "cumulative": round(cumulative, 4),
            })
        return result

    # ------------------------------------------------------------------
    # Loadings
    # ------------------------------------------------------------------

    def get_loadings(self, top_n: int = 10) -> Dict[str, List[Dict]]:
        """
        Returns top_n features per PC sorted by absolute loading.
        Format: {"PC1": [{"feature": ..., "loading": ..., "abs_loading": ...}], ...}
        """
        if self._pca is None or not self._feature_names:
            return {}

        components = self._pca.components_  # shape (n_components, n_features)
        result: Dict[str, List[Dict]] = {}

        for i, comp in enumerate(components):
            sorted_idx = np.argsort(np.abs(comp))[::-1][:top_n]
            pc_loadings = []
            for idx in sorted_idx:
                if idx < len(self._feature_names):
                    loading_val = float(comp[idx])
                    pc_loadings.append({
                        "feature": self._feature_names[idx],
                        "loading": round(loading_val, 6),
                        "abs_loading": round(abs(loading_val), 6),
                    })
            result[f"PC{i + 1}"] = pc_loadings

        return result

    # ------------------------------------------------------------------
    # Outlier Detection
    # ------------------------------------------------------------------

    def detect_outliers(self, projections: np.ndarray, threshold_std: float = 3.0) -> np.ndarray:
        """
        Detect outliers by distance from centroid in PC1+PC2 space.
        Returns boolean array: True = outlier.
        """
        if projections is None or projections.size == 0 or projections.shape[0] < 2:
            return np.array([], dtype=bool)

        n_cols = projections.shape[1]
        pc_slice = projections[:, :min(2, n_cols)]

        centroid = pc_slice.mean(axis=0)
        diff = pc_slice - centroid
        distances = np.sqrt((diff ** 2).sum(axis=1))

        mean_dist = distances.mean()
        std_dist = distances.std()

        if std_dist < 1e-10:
            return np.zeros(len(projections), dtype=bool)

        z_scores = (distances - mean_dist) / std_dist
        return z_scores > threshold_std

    # ------------------------------------------------------------------
    # Scree Data
    # ------------------------------------------------------------------

    def get_scree_data(self) -> Dict:
        """Returns eigenvalues and component names for scree plot."""
        if self._pca is None:
            return {"eigenvalues": [], "components": []}

        eigenvalues = [float(v) for v in self._pca.explained_variance_]
        components = [f"PC{i + 1}" for i in range(len(eigenvalues))]
        return {"eigenvalues": eigenvalues, "components": components}

    # ------------------------------------------------------------------
    # Full Analysis
    # ------------------------------------------------------------------

    def run_full_analysis(
        self,
        df: pd.DataFrame,
        descriptor_cols: List[str],
        smiles_col: Optional[str] = None,
        label_col: Optional[str] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        End-to-end PCA pipeline with progress reporting.

        Returns a JSON-serializable result dict.
        """

        def _cb(pct: int, phase: str):
            if progress_callback is not None:
                try:
                    progress_callback(pct, phase)
                except Exception:
                    pass

        # --- Edge case: empty input ---
        if df is None or df.empty or not descriptor_cols:
            return {
                "projections": [],
                "variance_explained": [],
                "top_features_per_pc": {},
                "scree_data": {"eigenvalues": [], "components": []},
                "outlier_indices": [],
                "outlier_count": 0,
                "n_components_used": 0,
                "n_components_95pct": 0,
                "n_features_used": 0,
                "n_features_dropped": 0,
                "n_samples": 0,
            }

        _cb(10, "Preparing descriptor matrix")
        X = self.prepare_matrix(df, descriptor_cols)
        n_features_dropped = self._n_features_dropped

        if X.size == 0 or X.shape[0] < 2:
            return {
                "projections": [],
                "variance_explained": [],
                "top_features_per_pc": {},
                "scree_data": {"eigenvalues": [], "components": []},
                "outlier_indices": [],
                "outlier_count": 0,
                "n_components_used": 0,
                "n_components_95pct": 0,
                "n_features_used": int(X.shape[1]) if X.ndim == 2 else 0,
                "n_features_dropped": n_features_dropped,
                "n_samples": int(X.shape[0]) if X.ndim == 2 else 0,
            }

        n_samples, n_features_used = int(X.shape[0]), int(X.shape[1])

        _cb(25, "Missing value handling")
        # (handled inside fit_transform → imputer)

        _cb(40, "Descriptor scaling")
        # (handled inside fit_transform → scaler)

        _cb(55, "PCA decomposition")
        try:
            projections = self.fit_transform(X)
        except Exception as exc:
            logger.error("PCA fit_transform failed: %s", exc)
            return {
                "projections": [],
                "variance_explained": [],
                "top_features_per_pc": {},
                "scree_data": {"eigenvalues": [], "components": []},
                "outlier_indices": [],
                "outlier_count": 0,
                "n_components_used": 0,
                "n_components_95pct": 0,
                "n_features_used": n_features_used,
                "n_features_dropped": n_features_dropped,
                "n_samples": n_samples,
            }

        if projections.size == 0:
            n_comp_used = 0
        else:
            n_comp_used = int(projections.shape[1])

        _cb(70, "Variance calculations")
        variance_explained = self.compute_variance_explained()

        # How many components to explain 95%?
        n_components_95pct = 0
        cumulative = 0.0
        for ve in variance_explained:
            cumulative += ve["variance_pct"]
            n_components_95pct += 1
            if cumulative >= 95.0:
                break

        _cb(80, "Loading matrix generation")
        top_features_per_pc = self.get_loadings(top_n=10)
        scree_data = self.get_scree_data()

        _cb(90, "Outlier detection")
        outlier_mask = self.detect_outliers(projections, threshold_std=3.0)

        # Build projection records
        smiles_values: List[Optional[str]] = []
        if smiles_col and smiles_col in df.columns:
            smiles_values = df[smiles_col].fillna("").tolist()
        else:
            smiles_values = [""] * n_samples

        label_values: List[Any] = []
        if label_col and label_col in df.columns:
            label_values = df[label_col].tolist()
        else:
            label_values = [None] * n_samples

        projection_records = []
        n_pcs = projections.shape[1] if projections.size > 0 else 0
        outlier_indices: List[int] = []

        for i in range(n_samples):
            rec: Dict[str, Any] = {"idx": i}
            rec["smiles"] = str(smiles_values[i]) if i < len(smiles_values) else ""
            for pc_idx in range(n_pcs):
                rec[f"PC{pc_idx + 1}"] = round(float(projections[i, pc_idx]), 6)

            is_out = bool(outlier_mask[i]) if i < len(outlier_mask) else False
            rec["is_outlier"] = is_out
            if is_out:
                outlier_indices.append(i)

            lv = label_values[i] if i < len(label_values) else None
            try:
                rec["label"] = float(lv) if lv is not None and lv == lv else None  # NaN check
            except (TypeError, ValueError):
                rec["label"] = str(lv) if lv is not None else None

            projection_records.append(rec)

        _cb(100, "Complete")

        return {
            "projections": projection_records,
            "variance_explained": variance_explained,
            "top_features_per_pc": top_features_per_pc,
            "scree_data": scree_data,
            "outlier_indices": [int(x) for x in outlier_indices],
            "outlier_count": int(len(outlier_indices)),
            "n_components_used": n_comp_used,
            "n_components_95pct": int(n_components_95pct),
            "n_features_used": n_features_used,
            "n_features_dropped": int(n_features_dropped),
            "n_samples": n_samples,
        }

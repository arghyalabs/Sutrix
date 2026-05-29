"""
Feature Engineering Advisor — generates prioritized preprocessing recommendations
from pre-computed intelligence layer metrics.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List


def advise_features(
    df: pd.DataFrame,
    mappings: Dict[str, str],
    descriptor_result: Dict[str, Any],
    missingness_result: Dict[str, Any],
    correlation_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Returns a prioritized list of feature engineering recommendations."""
    recommendations = []
    sci_to_user = {v: k for k, v in mappings.items()}
    val_col = sci_to_user.get("value")
    smiles_col = sci_to_user.get("canonical_smiles")
    unit_col = sci_to_user.get("unit")
    ep_col = sci_to_user.get("endpoint")

    # --- 1. Drop hard_exclusion descriptors (>70% missing) ---
    hard_excl = descriptor_result.get("hard_exclusion", [])
    if hard_excl:
        cols = [d["name"] for d in hard_excl]
        recommendations.append({
            "id": "drop_hard_exclusion",
            "action": "Drop High-Sparsity Descriptors",
            "severity": "CRITICAL",
            "affected_columns": cols[:10],  # show first 10
            "affected_count": len(cols),
            "reasoning": f"{len(cols)} descriptor(s) have >70% missing values. Including them will corrupt any model.",
            "expected_impact": f"Removes {len(cols)} noise columns. Reduces dimensionality.",
            "auto_applicable": True,
            "code_hint": f"df.drop(columns={cols[:3]}{'...' if len(cols)>3 else ''}, inplace=True)",
        })

    # --- 2. Remove exact duplicates ---
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        recommendations.append({
            "id": "remove_duplicates",
            "action": "Remove Exact Duplicate Rows",
            "severity": "CRITICAL" if dup_count / len(df) > 0.1 else "HIGH",
            "affected_columns": [],
            "affected_count": int(dup_count),
            "reasoning": f"{dup_count} exact duplicate rows found. These bias training and inflate performance metrics.",
            "expected_impact": "Eliminates data leakage from identical train/test samples.",
            "auto_applicable": True,
            "code_hint": "df.drop_duplicates(inplace=True)",
        })

    # --- 3. Recommend pruning descriptors (40-70% missing) ---
    rec_prune = descriptor_result.get("recommend_pruning", [])
    if rec_prune:
        cols = [d["name"] for d in rec_prune]
        recommendations.append({
            "id": "prune_moderate_sparse",
            "action": "Review or Impute Moderately Sparse Descriptors",
            "severity": "HIGH",
            "affected_columns": cols[:10],
            "affected_count": len(cols),
            "reasoning": f"{len(cols)} descriptor(s) have 40–70% missing values. Imputation will distort their distributions.",
            "expected_impact": "Use median imputation or drop depending on scientific relevance.",
            "auto_applicable": False,
            "code_hint": f"df[{cols[:2]}].fillna(df[{cols[:2]}].median(), inplace=True)",
        })

    # --- 4. Drop near-zero variance descriptors ---
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    exclude = [val_col, smiles_col, unit_col, ep_col]
    descriptor_cols = [c for c in numeric_cols if c not in exclude and c]
    low_var_cols = []
    for col in descriptor_cols:
        v = df[col].var()
        if pd.notna(v) and v < 1e-4:
            low_var_cols.append(col)
    if low_var_cols:
        recommendations.append({
            "id": "drop_low_variance",
            "action": "Drop Near-Zero Variance Descriptors",
            "severity": "HIGH",
            "affected_columns": low_var_cols[:10],
            "affected_count": len(low_var_cols),
            "reasoning": f"{len(low_var_cols)} descriptor(s) are nearly constant (var < 1e-4). They contribute no signal.",
            "expected_impact": "Reduces dimensionality without information loss.",
            "auto_applicable": True,
            "code_hint": "from sklearn.feature_selection import VarianceThreshold\nVT = VarianceThreshold(threshold=1e-4)\ndf_reduced = pd.DataFrame(VT.fit_transform(df), columns=df.columns[VT.get_support()])",
        })

    # --- 5. Log-transform skewed endpoint ---
    if val_col and val_col in df.columns:
        numeric_vals = pd.to_numeric(df[val_col], errors="coerce").dropna()
        if len(numeric_vals) > 10:
            skew = numeric_vals.skew()
            if abs(skew) > 2.0 and (numeric_vals > 0).all():
                recommendations.append({
                    "id": "log_transform_endpoint",
                    "action": f"Log-Transform Target Column '{val_col}'",
                    "severity": "HIGH",
                    "affected_columns": [val_col],
                    "affected_count": 1,
                    "reasoning": f"Target endpoint skewness is {skew:.2f}. Log-transform linearizes the SAR and stabilizes model training.",
                    "expected_impact": "Significantly improves R² and residual normality for regression models.",
                    "auto_applicable": True,
                    "code_hint": f"import numpy as np\ndf['{val_col}_log'] = np.log10(df['{val_col}'])",
                })

    # --- 6. Standardize descriptors with large scale differences ---
    if descriptor_cols:
        sample_df = df[descriptor_cols].select_dtypes(include=[np.number])
        if not sample_df.empty:
            col_ranges = sample_df.max() - sample_df.min()
            wide_range_cols = col_ranges[col_ranges > 1000].index.tolist()
            if wide_range_cols:
                recommendations.append({
                    "id": "standardize_features",
                    "action": "Standardize Wide-Range Descriptors",
                    "severity": "MEDIUM",
                    "affected_columns": wide_range_cols[:10],
                    "affected_count": len(wide_range_cols),
                    "reasoning": f"{len(wide_range_cols)} descriptor(s) have value ranges >1000. Distance-based models (SVM, KNN) are severely affected by scale differences.",
                    "expected_impact": "Equalizes descriptor contributions. Required before SVM or KNN.",
                    "auto_applicable": True,
                    "code_hint": "from sklearn.preprocessing import StandardScaler\nscaler = StandardScaler()\ndf[descriptor_cols] = scaler.fit_transform(df[descriptor_cols])",
                })

    # --- 7. Remove highly correlated descriptor pairs ---
    redundant_pairs = correlation_result.get("redundant_pairs", [])
    if redundant_pairs:
        # Collect unique candidates to drop (second of each pair)
        to_drop = list({p["Descriptor 2"] for p in redundant_pairs})
        recommendations.append({
            "id": "drop_correlated",
            "action": "Remove Highly Correlated Descriptors (r > 0.90)",
            "severity": "MEDIUM",
            "affected_columns": to_drop[:10],
            "affected_count": len(to_drop),
            "reasoning": f"{len(redundant_pairs)} descriptor pair(s) have Pearson r > 0.90. Multicollinearity inflates variance in linear models.",
            "expected_impact": "Reduces multicollinearity. Improves linear model coefficient stability.",
            "auto_applicable": True,
            "code_hint": f"# Drop one from each correlated pair\ndrop_cols = {to_drop[:3]}\ndf.drop(columns=drop_cols, inplace=True)",
        })

    # --- 8. Encode qualifier column if present ---
    qual_col = sci_to_user.get("qualifier")
    if qual_col and qual_col in df.columns:
        unique_quals = df[qual_col].dropna().unique().tolist()
        if len(unique_quals) > 1:
            recommendations.append({
                "id": "encode_qualifier",
                "action": f"Encode Qualifier Column '{qual_col}'",
                "severity": "MEDIUM",
                "affected_columns": [qual_col],
                "affected_count": 1,
                "reasoning": f"Qualifier column contains mixed values {unique_quals[:5]}. Encode as ordinal (<=-1, ==0, >=+1) for modeling.",
                "expected_impact": "Converts inequality notation to numeric signal usable by all models.",
                "auto_applicable": True,
                "code_hint": f"qual_map = {{'<': -1, '=': 0, '>': 1}}\ndf['{qual_col}_enc'] = df['{qual_col}'].map(qual_map).fillna(0)",
            })

    # Sort by severity
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    recommendations.sort(key=lambda r: order.get(r["severity"], 4))
    return recommendations

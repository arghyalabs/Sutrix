import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
import math
import time
import concurrent.futures

class DatasetReadinessScorer:
    """
    Computes a comprehensive Dataset Readiness Score (DRS) indicating 
    suitability of a scientific dataset for AI/QSAR modeling.
    """
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "missing_values": 0.20,
            "structural_completeness": 0.20,
            "variance_quality": 0.15,
            "sample_size": 0.15,
            "class_balance": 0.10,
            "duplicate_ratio": 0.10,
            "endpoint_uniformity": 0.10
        }
        
    def evaluate(self, df: pd.DataFrame, mappings: Dict[str, str]) -> Dict[str, Any]:
        scores = {}
        deductions = []
        
        # Invert mappings for reverse lookup
        sci_to_user = {v: k for k, v in mappings.items()}
        
        # 1. Missing Values (Target: 0% missingness)
        # Check overall null pct across mapped columns
        mapped_cols = [col for col in df.columns if col in column_keys_mapped(mappings)]
        if mapped_cols:
            missing_pct = df[mapped_cols].isnull().mean().mean() * 100
        else:
            missing_pct = df.isnull().mean().mean() * 100
        scores["missing_values"] = max(0.0, 100.0 - (missing_pct * 3.0))
        if missing_pct > 10.0:
            deductions.append(f"Missing values average is high ({missing_pct:.1f}% across mapped columns).")
        
        # 2. Structural Completeness (SMILES)
        smiles_col = sci_to_user.get('canonical_smiles')
        if smiles_col and smiles_col in df.columns:
            empty_smiles = df[smiles_col].isnull().sum()
            smiles_score = max(0.0, 100.0 - (empty_smiles / len(df) * 100.0))
            scores["structural_completeness"] = smiles_score
            if empty_smiles > 0:
                deductions.append(f"{empty_smiles} records lack structural SMILES notation.")
        else:
            scores["structural_completeness"] = 0.0
            deductions.append("Critical: No structural SMILES column mapped in the dataset.")
            
        # 3. Variance Quality (prune near-zero variance features)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        # Exclude value column from variance quality features checklist
        val_col = sci_to_user.get('value')
        features = [col for col in numeric_cols if col != val_col]
        
        if len(features) > 0:
            low_var_count = 0
            for col in features:
                # Catch near-constant columns
                if df[col].var() < 1e-4 or pd.isnull(df[col].var()):
                    low_var_count += 1
            scores["variance_quality"] = max(0.0, 100.0 - (low_var_count / len(features) * 100.0))
            if low_var_count > 0:
                deductions.append(f"Identified {low_var_count} descriptors with near-zero or constant variance.")
        else:
            scores["variance_quality"] = 100.0 # Default if no descriptor features are mapped yet
            
        # 4. Sample Size
        n_samples = len(df)
        if n_samples >= 500:
            scores["sample_size"] = 100.0
        elif n_samples >= 100:
            scores["sample_size"] = 70.0 + (n_samples - 100) * (30.0 / 400.0)
        else:
            scores["sample_size"] = max(0.0, n_samples * 0.7)
            deductions.append(f"Low sample size ({n_samples} records). Modelability is limited.")
            
        # 5. Class Balance / Potency Skewness
        target_col = sci_to_user.get('value')
        if target_col and target_col in df.columns:
            # Check if continuous or discrete
            unique_vals = df[target_col].dropna().nunique()
            if unique_vals <= 5:  # Discrete/Classification
                counts = df[target_col].value_counts(normalize=True)
                majority_pct = counts.iloc[0] if len(counts) > 0 else 1.0
                scores["class_balance"] = max(0.0, 100.0 - (majority_pct - 0.5) * 200.0)
                if majority_pct > 0.75:
                    deductions.append(f"Severe class imbalance: majority class represents {majority_pct*100:.1f}% of data.")
            else:  # Continuous/Regression
                skew = abs(df[target_col].skew())
                if pd.isnull(skew):
                    scores["class_balance"] = 100.0
                else:
                    scores["class_balance"] = max(0.0, 100.0 - (skew * 20.0))
                    if skew > 1.5:
                        deductions.append(f"High potency distribution skewness ({skew:.2f}). Consider log-transform.")
        else:
            scores["class_balance"] = 0.0
            deductions.append("Target potency values are missing or unmapped.")
            
        # 6. Duplicate Ratio
        dup_count = df.duplicated().sum()
        scores["duplicate_ratio"] = max(0.0, 100.0 - (dup_count / len(df) * 200.0))
        if dup_count > 0:
            deductions.append(f"Duplicate records found: {dup_count} duplicates detected.")
            
        # 7. Endpoint Uniformity
        unit_col = sci_to_user.get('unit')
        if unit_col and unit_col in df.columns:
            unique_units = df[unit_col].dropna().nunique()
            scores["endpoint_uniformity"] = 100.0 if unique_units == 1 else 30.0
            if unique_units > 1:
                deductions.append(f"Multi-unit inconsistency: {unique_units} different assay units present.")
        else:
            scores["endpoint_uniformity"] = 100.0
            
        # Compile score
        final_score = sum(scores[k] * self.weights[k] for k in self.weights)
        
        tier = "Tier A (AI Ready)" if final_score >= 85 else "Tier B (Requires Curation)" if final_score >= 60 else "Tier C (Not Modeling Fit)"
        
        # --- Streamlit Parity: OECD Scoring ---
        from backend.core.scientific_runtime import ScientificRuntime
        oecd_res = ScientificRuntime.calculate_oecd_score(df, mappings)
        
        # Merge the AI generic breakdown into the OECD breakdown
        oecd_res["breakdown"].update({k: round(v, 1) for k, v in scores.items()})
        
        # Combine deductions
        for d in deductions:
            if d not in oecd_res["deductions"]:
                oecd_res["deductions"].append(d)
                
        return oecd_res


class DescriptorReliabilityEngine:
    """
    Evaluates topological and chemical descriptor columns, tracking failure frequencies,
    missing rates, and calculation errors, then categorizes them for soft-pruning.
    """
    @staticmethod
    def evaluate_descriptors(df: pd.DataFrame, mappings: Dict[str, str]) -> Dict[str, Any]:
        sci_to_user = {v: k for k, v in mappings.items()}
        smiles_col = sci_to_user.get('canonical_smiles')
        val_col = sci_to_user.get('value')
        unit_col = sci_to_user.get('unit')
        ep_col = sci_to_user.get('endpoint')
        chem_col = sci_to_user.get('chemical_name') or sci_to_user.get('chemical_id') or sci_to_user.get('cas_number')
        
        system_cols = [smiles_col, val_col, unit_col, ep_col, chem_col, 'audit_flag', 'session_id']
        descriptor_cols = [c for c in df.columns if c not in system_cols and df[c].dtype in [np.float64, np.int64, object]]
        
        evaluation = {
            "keep": [],
            "moderate_warning": [],
            "recommend_pruning": [],
            "hard_exclusion": [],
            "descriptor_reliability_score": 100.0
        }
        
        if not descriptor_cols:
            return evaluation
            
        total_records = len(df)
        unstable_count = 0
        
        for col in descriptor_cols:
            raw_vals = df[col].astype(str)
            
            # Count explicit error codes generated by Mordred/RDKit (e.g. exceptions or NaN)
            errors = raw_vals.str.contains("error|fail|exception|nan|none|null", case=False, na=True).sum()
            missing_pct = (errors / total_records) * 100.0
            
            meta = {
                "name": col,
                "sparsity": round(missing_pct, 2),
                "calculation_failures": int(errors),
                "type": str(df[col].dtype)
            }
            
            # Sparsity categorization rules approved by user:
            if missing_pct < 10.0:
                evaluation["keep"].append(meta)
            elif 10.0 <= missing_pct <= 40.0:
                evaluation["moderate_warning"].append(meta)
                unstable_count += 0.2
            elif 40.0 < missing_pct <= 70.0:
                evaluation["recommend_pruning"].append(meta)
                unstable_count += 0.6
            else:
                evaluation["hard_exclusion"].append(meta)
                unstable_count += 1.0
                
        # Calculate Descriptor Reliability Score
        score = max(0.0, 100.0 - (unstable_count / len(descriptor_cols) * 100.0)) if len(descriptor_cols) > 0 else 100.0
        evaluation["descriptor_reliability_score"] = round(score, 1)
        
        return evaluation


class ChemicalDiversityScorer:
    """
    Computes molecular library diversity using RDKit-based fingerprint Tanimoto similarities.
    """
    @staticmethod
    def calculate_diversity(df: pd.DataFrame, mappings: Dict[str, str]) -> Dict[str, Any]:
        sci_to_user = {v: k for k, v in mappings.items()}
        smiles_col = sci_to_user.get('canonical_smiles')
        
        if not smiles_col or smiles_col not in df.columns:
            return {
                "status": "Skipped",
                "mean_tanimoto_similarity": 0.0,
                "chemical_diversity_score": 0.0,
                "interpretation": "Lacks mapped SMILES notation."
            }
            
        smiles_series = df[smiles_col].dropna().drop_duplicates()
        if len(smiles_series) < 2:
            return {
                "status": "Skipped",
                "mean_tanimoto_similarity": 0.0,
                "chemical_diversity_score": 0.0,
                "interpretation": "Insufficient unique compounds to measure diversity."
            }
            
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
            from rdkit import DataStructs
        except ImportError:
            return {
                "status": "Skipped",
                "mean_tanimoto_similarity": 0.5,
                "chemical_diversity_score": 0.5,
                "interpretation": "RDKit is not installed locally. Dynamic chemical diversity estimation is offline."
            }
            
        # Sample to prevent computational blowout on huge databases (sample 150)
        sample_size = min(len(smiles_series), 150)
        sampled_smiles = smiles_series.sample(n=sample_size, random_state=42)
        
        mols = []
        for s in sampled_smiles:
            try:
                mol = Chem.MolFromSmiles(s)
                if mol:
                    mols.append(AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024))
            except Exception:
                continue
                
        if len(mols) < 2:
            return {
                "status": "Failed",
                "mean_tanimoto_similarity": 0.0,
                "chemical_diversity_score": 0.0,
                "interpretation": "RDKit could not parse the structural SMILES strings."
            }
            
        similarities = []
        for i in range(len(mols)):
            for j in range(i + 1, len(mols)):
                sim = DataStructs.TanimotoSimilarity(mols[i], mols[j])
                similarities.append(sim)
                
        mean_sim = np.mean(similarities)
        diversity_score = 1.0 - mean_sim
        
        interpretation = "High Diversity (Broad chemical library)" if diversity_score > 0.6 else "Low Diversity (Highly homogeneous structural analogues)"
        
        return {
            "status": "Success",
            "mean_tanimoto_similarity": round(float(mean_sim), 3),
            "chemical_diversity_score": round(float(diversity_score), 3),
            "interpretation": interpretation
        }


class ScaffoldLeakageAuditor:
    """
    Audits compound skeletons using Bemis-Murcko scaffolds to flag structural data leakage risks.
    """
    @staticmethod
    def audit_scaffolds(df: pd.DataFrame, mappings: Dict[str, str]) -> Dict[str, Any]:
        sci_to_user = {v: k for k, v in mappings.items()}
        smiles_col = sci_to_user.get('canonical_smiles')
        
        if not smiles_col or smiles_col not in df.columns:
            return {
                "status": "Skipped",
                "total_scaffolds": 0,
                "scaffold_imbalance_level": "None",
                "details": "SMILES structures unavailable."
            }
            
        try:
            from rdkit import Chem
            from rdkit.Chem.Scaffolds import MurckoScaffold
        except ImportError:
            return {
                "status": "Skipped",
                "total_scaffolds": 0,
                "scaffold_imbalance_level": "Unknown",
                "details": "RDKit is not installed. Scaffold audit is offline."
            }
            
        scaffold_counts = {}
        valid_records = 0
        
        for s in df[smiles_col].dropna():
            try:
                mol = Chem.MolFromSmiles(s)
                if mol:
                    scaf = MurckoScaffold.GetScaffoldForMol(mol)
                    scaf_smiles = Chem.MolToSmiles(scaf)
                    scaffold_counts[scaf_smiles] = scaffold_counts.get(scaf_smiles, 0) + 1
                    valid_records += 1
            except Exception:
                continue
                
        if not scaffold_counts:
            return {
                "status": "Failed",
                "total_scaffolds": 0,
                "scaffold_imbalance_level": "None",
                "details": "Could not extract Bemis-Murcko skeletons."
            }
            
        total_scaffolds = len(scaffold_counts)
        singletons = sum(1 for c in scaffold_counts.values() if c == 1)
        max_cluster_size = max(scaffold_counts.values())
        cluster_ratio = max_cluster_size / valid_records if valid_records > 0 else 0
        
        if cluster_ratio > 0.25:
            imbalance = "High Scaffold Leakage Risk"
            details = f"Heavy scaffold concentration found. The top cluster represents {cluster_ratio*100:.1f}% of structures. Random cross-validation will overfit."
        elif cluster_ratio > 0.10:
            imbalance = "Moderate Scaffold Leakage Risk"
            details = f"Some structural clustering present. The largest skeleton represents {cluster_ratio*100:.1f}% of data."
        else:
            imbalance = "Low Scaffold Leakage Risk"
            details = "Compounds are structurally dispersed. Standard cross-validation splits are relatively safe."
            
        return {
            "status": "Success",
            "total_scaffolds": total_scaffolds,
            "singleton_scaffolds": singletons,
            "largest_scaffold_cluster_size": max_cluster_size,
            "scaffold_imbalance_level": imbalance,
            "details": details
        }


class SuccessEstimator:
    """
    Implements the two-tier predictive success confidence engine.
    """
    @staticmethod
    def run_level1_quick(df: pd.DataFrame, mappings: Dict[str, str]) -> Dict[str, Any]:
        sci_to_user = {v: k for k, v in mappings.items()}
        target_col = sci_to_user.get('value')
        
        if not target_col or target_col not in df.columns:
            return {
                "confidence": "Low",
                "baseline_performance": 0.0,
                "reason": "Target potency variable is unmapped."
            }
            
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        feature_cols = [c for c in numeric_cols if c != target_col and c not in ['session_id']]
        
        if not feature_cols:
            return {
                "confidence": "Low",
                "baseline_performance": 0.0,
                "reason": "No numerical descriptor columns available for training."
            }
            
        # Clean target
        y_clean = pd.to_numeric(df[target_col], errors='coerce').dropna()
        if len(y_clean) < 10:
            return {
                "confidence": "Low",
                "baseline_performance": 0.0,
                "reason": "Insufficient valid numerical target values."
            }
            
        # Build features
        X_clean = df.loc[y_clean.index, feature_cols].fillna(df[feature_cols].median())
        
        # Subsample to keep processing strictly within 30s cap
        if len(X_clean) > 8000:
            idx = X_clean.sample(n=8000, random_state=42).index
            X_clean = X_clean.loc[idx]
            y_clean = y_clean.loc[idx]
            
        n_samples, n_features = X_clean.shape
        ratio = n_samples / max(1, n_features)
        
        # Determine classification vs regression
        unique_targets = y_clean.nunique()
        is_classification = unique_targets <= 5
        
        # Fast ANOVA selection to prevent dimensionality blowout
        from sklearn.feature_selection import SelectKBest, f_regression, f_classif
        from sklearn.linear_model import RidgeCV, LogisticRegressionCV
        
        k = min(30, n_features)
        selector = SelectKBest(score_func=f_classif if is_classification else f_regression, k=k)
        
        try:
            X_sel = selector.fit_transform(X_clean, y_clean)
            if is_classification:
                # Quick regularized logistic regression
                model = LogisticRegressionCV(cv=3, max_iter=300, class_weight='balanced', solver='liblinear')
                # Wrap with a timeout guard
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(model.fit, X_sel, y_clean)
                    fitted = future.result(timeout=25)
                    score = float(fitted.score(X_sel, y_clean))
                metric_name = "Balanced Accuracy Proxy"
            else:
                model = RidgeCV(cv=3)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(model.fit, X_sel, y_clean)
                    fitted = future.result(timeout=25)
                    score = float(fitted.score(X_sel, y_clean))
                metric_name = "Coefficient of Determination (R2)"
        except Exception as e:
            score = 0.0
            return {
                "confidence": "Low",
                "baseline_performance": 0.0,
                "reason": f"Baseline modeling training failed or timed out: {str(e)}"
            }
            
        # Modeling Heuristics
        if ratio < 3.0 or score < 0.1:
            confidence = "Low Predictive Confidence"
            reason = f"Poor structural-activity signal or extremely small sample size relative to descriptor scale (N/P: {ratio:.1f})."
        elif ratio < 10.0 or score < 0.45:
            confidence = "Moderate Predictive Confidence"
            reason = "Sufficient correlation present for simple linear/tree estimators. Advanced neural networks are likely to overfit."
        else:
            confidence = "High Predictive Confidence"
            reason = f"Robust baseline modeling performance ({metric_name}: {score:.2f}) with a safe sample to descriptor scale."
            
        return {
            "confidence": confidence,
            "baseline_performance": round(score, 3),
            "metric_name": metric_name,
            "n_to_p_ratio": round(ratio, 2),
            "reason": reason
        }


class ScientificIntelligenceEngine:
    """
    Evaluates unit anomalies, assay harmonization consistency, and experimental duplication noise.
    """
    @staticmethod
    def audit_endpoint_harmonization(df: pd.DataFrame, mappings: Dict[str, str]) -> Dict[str, Any]:
        findings = []
        sci_to_user = {v: k for k, v in mappings.items()}
        unit_col = sci_to_user.get('unit')
        ep_col = sci_to_user.get('endpoint')
        
        if unit_col and unit_col in df.columns:
            unique_units = df[unit_col].dropna().astype(str).str.strip().unique()
            if len(unique_units) > 1:
                findings.append({
                    "severity": "Critical",
                    "issue": "Mixed Assay Units Detected",
                    "details": f"Dataset contains mixed concentration/dose metrics: {list(unique_units)}. Modeling mixed units violates physical-chemical equivalence."
                })
                
        if ep_col and ep_col in df.columns:
            unique_eps = df[ep_col].dropna().astype(str).str.strip().unique()
            if len(unique_eps) > 1:
                findings.append({
                    "severity": "Warning",
                    "issue": "Mixed Biological Endpoints",
                    "details": f"Multi-task biological endpoints detected: {list(unique_eps)}. Ensure data is segregated or multi-task modeling architectures are configured."
                })
                
        return {
            "harmonized": len(findings) == 0,
            "findings": findings
        }
        
    @staticmethod
    def detect_experimental_noise(df: pd.DataFrame, mappings: Dict[str, str]) -> Dict[str, Any]:
        sci_to_user = {v: k for k, v in mappings.items()}
        smiles_col = sci_to_user.get('canonical_smiles')
        target_col = sci_to_user.get('value')
        ep_col = sci_to_user.get('endpoint')
        unit_col = sci_to_user.get('unit')
        
        if not smiles_col or not target_col or smiles_col not in df.columns or target_col not in df.columns:
            return {"noise_detected": False, "conflicts": []}
            
        # Group keys: compound structure + endpoint + unit (if mapped)
        group_keys = [smiles_col]
        if ep_col and ep_col in df.columns:
            group_keys.append(ep_col)
        if unit_col and unit_col in df.columns:
            group_keys.append(unit_col)
            
        # Filter negative or null potencies
        numeric_vals = pd.to_numeric(df[target_col], errors='coerce')
        valid_df = df[numeric_vals > 0].copy()
        valid_df['_val_num'] = numeric_vals[numeric_vals > 0]
        
        if len(valid_df) == 0:
            return {"noise_detected": False, "conflicts": []}
            
        # Find duplicates
        grouped = valid_df.groupby(group_keys)['_val_num'].agg(['count', 'min', 'max'])
        duplicates = grouped[grouped['count'] > 1]
        
        conflicts = []
        for idx, row in duplicates.iterrows():
            min_val = float(row['min'])
            max_val = float(row['max'])
            
            # Log range range check
            log_range = np.log10(max_val) - np.log10(min_val)
            if log_range >= 1.0: # 10x or greater range
                name = idx if isinstance(idx, str) else idx[0]
                conflicts.append({
                    "compound": name,
                    "count": int(row['count']),
                    "min_val": min_val,
                    "max_val": max_val,
                    "log_range": round(log_range, 2)
                })
                
        return {
            "noise_detected": len(conflicts) > 0,
            "conflict_count": len(conflicts),
            "conflicts": conflicts
        }


# Helper utilities
def column_keys_mapped(mappings: Dict[str, str]) -> List[str]:
    return list(mappings.keys())

import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List

from .duplicate_detection import DuplicateDetection
from .conflict_detection import ConflictDetection
from .missingness_analysis import MissingnessAnalysis
from .descriptor_correlation import DescriptorCorrelation

class DatasetHealthIntelligence:
    """
    Central orchestration layer for analyzing dataset quality, health, and scientific consistency.
    Generates an overall Health Score out of 100 and comprehensive actionable recommendations.
    """
    
    @staticmethod
    def calculate_health_score(metrics: Dict[str, Any]) -> int:
        score = 100
        
        # Deductions
        miss_pct = metrics.get("missingness", {}).get("overall_missing_pct", 0)
        score -= min(30, (miss_pct / 100) * 40) # Max 30 points lost for missing data
        
        total_rows = metrics.get("total_rows", 1)
        
        dups = metrics.get("duplicates", {}).get("exact_duplicates", 0)
        dup_pct = (dups / total_rows) * 100
        score -= min(20, dup_pct * 2) # Max 20 points lost for duplicates
        
        conflicts = metrics.get("conflicts", {}).get("conflicts_count", 0)
        conf_pct = (conflicts / total_rows) * 100
        score -= min(30, conf_pct * 5) # Heavy penalty for conflicts
        
        redundancy = metrics.get("correlations", {}).get("redundant_count", 0)
        score -= min(20, redundancy) # Max 20 points lost for excessive collinearity
        
        return max(0, int(score))

    @staticmethod
    def generate_recommendations(metrics: Dict[str, Any]) -> List[str]:
        recs = []
        if metrics.get("missingness", {}).get("overall_missing_pct", 0) > 10:
            recs.append("⚠️ High Missingness: Consider running the imputation engine or API enrichment pipeline to fill gaps.")
            
        if metrics.get("duplicates", {}).get("exact_duplicates", 0) > 0:
            recs.append("🔍 Exact Duplicates Found: Apply standard deduplication on structural identity.")
            
        if metrics.get("conflicts", {}).get("conflicts_count", 0) > 0:
            recs.append("🚨 Scientific Conflicts Detected: High-variance conflicting endpoints found. Resolve via mean averaging or pruning.")
            
        if metrics.get("correlations", {}).get("redundant_count", 0) > 0:
            recs.append("📉 Collinearity Warning: Highly correlated descriptors identified. Consider PCA or dropping redundant features before QSAR modeling.")
            
        if not recs:
            recs.append("✅ Dataset is pristine and QSAR-ready.")
            
        return recs

    @staticmethod
    def generate_gauge_chart(score: int):
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Dataset Health Score"},
            gauge = {
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#2ecc71" if score > 80 else ("#f1c40f" if score > 50 else "#e74c3c")},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 50], 'color': '#ffcccc'},
                    {'range': [50, 80], 'color': '#ffffcc'},
                    {'range': [80, 100], 'color': '#ccffcc'}],
            }
        ))
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        return fig

    @classmethod
    def analyze_dataset(cls, df: pd.DataFrame, structure_col: str, endpoint_col: str, descriptor_cols: List[str]) -> Dict[str, Any]:
        """Runs the full Intelligence Layer analysis suite."""
        
        metrics = {
            "total_rows": len(df),
            "duplicates": DuplicateDetection.analyze(df, structure_col, endpoint_col),
            "conflicts": ConflictDetection.analyze(df, structure_col, endpoint_col),
            "missingness": MissingnessAnalysis.analyze(df, target_cols=[structure_col, endpoint_col] + descriptor_cols),
            "correlations": DescriptorCorrelation.analyze(df, descriptor_cols)
        }
        
        metrics["health_score"] = cls.calculate_health_score(metrics)
        metrics["recommendations"] = cls.generate_recommendations(metrics)
        metrics["gauge_figure"] = cls.generate_gauge_chart(metrics["health_score"])
        
        return metrics

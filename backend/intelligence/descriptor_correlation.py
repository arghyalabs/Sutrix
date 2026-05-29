import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List

class DescriptorCorrelation:
    """Analyzes linear correlation between descriptors to detect mathematical redundancy."""
    @staticmethod
    def analyze(df: pd.DataFrame, descriptor_cols: List[str], threshold: float = 0.90) -> Dict[str, Any]:
        """Detects highly redundant (correlated) descriptors."""
        cols = [c for c in descriptor_cols if c in df.columns]
        if not cols or len(cols) < 2:
            return {"redundant_pairs": [], "redundant_count": 0, "figure": None}
            
        numeric_df = df[cols].apply(pd.to_numeric, errors='coerce')
        # Drop columns that are completely NaN
        numeric_df = numeric_df.dropna(axis=1, how='all')
        
        if numeric_df.shape[1] < 2:
            return {"redundant_pairs": [], "redundant_count": 0, "figure": None}

        corr_matrix = numeric_df.corr(method='pearson')
        
        # Find highly correlated pairs
        pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                val = corr_matrix.iloc[i, j]
                if pd.notna(val) and abs(val) >= threshold:
                    pairs.append({
                        "Descriptor 1": corr_matrix.columns[i],
                        "Descriptor 2": corr_matrix.columns[j],
                        "Correlation": float(val)
                    })
                    
        # Generate premium heatmap
        fig = go.Figure(data=go.Heatmap(
                   z=corr_matrix.values,
                   x=corr_matrix.columns,
                   y=corr_matrix.columns,
                   colorscale='RdBu',
                   zmin=-1, zmax=1,
                   hoverongaps=False))
                   
        fig.update_layout(
            title="Descriptor Correlation Matrix (Collinearity Analysis)",
            xaxis_nticks=36,
            template="plotly_white",
            height=600, width=600
        )
        
        return {
            "redundant_pairs": pairs,
            "redundant_count": len(pairs),
            "figure": fig
        }

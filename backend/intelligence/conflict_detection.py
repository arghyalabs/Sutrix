import pandas as pd
import numpy as np
from typing import Dict, Any

class ConflictDetection:
    """Analyzes structural duplicates that present conflicting biological data."""
    @staticmethod
    def analyze(df: pd.DataFrame, structure_col: str, endpoint_col: str, variance_threshold: float = 1.0) -> Dict[str, Any]:
        """Detects structurally identical compounds with conflicting biological endpoints."""
        if structure_col not in df.columns or endpoint_col not in df.columns:
            return {"conflicts_count": 0, "conflict_groups": 0, "details": []}
            
        # Group by structure and find std / variance in endpoint
        valid_df = df.dropna(subset=[structure_col, endpoint_col]).copy()
        
        # Ensure endpoint is numeric
        valid_df[endpoint_col] = pd.to_numeric(valid_df[endpoint_col], errors='coerce')
        valid_df = valid_df.dropna(subset=[endpoint_col])
        
        grouped = valid_df.groupby(structure_col)[endpoint_col].agg(['count', 'std', 'max', 'min'])
        
        # Filter groups with >1 entry and std dev > threshold or range > threshold
        conflicting = grouped[(grouped['count'] > 1) & ((grouped['max'] - grouped['min']) > variance_threshold)]
        
        return {
            "conflicts_count": int(conflicting['count'].sum()) if not conflicting.empty else 0,
            "conflict_groups": len(conflicting),
            "details": conflicting.reset_index().to_dict(orient='records')
        }

import pandas as pd
from typing import Dict, Any

class DuplicateDetection:
    """Analyzes datasets for structural and endpoint exact duplicates."""
    @staticmethod
    def analyze(df: pd.DataFrame, structure_col: str, endpoint_col: str) -> Dict[str, Any]:
        """Detects exact structural duplicates matching the same endpoint."""
        if structure_col not in df.columns or endpoint_col not in df.columns:
            return {"exact_duplicates": 0, "duplicate_groups": 0, "details": []}
            
        # Clean structural column
        valid_df = df.dropna(subset=[structure_col])
        duplicates = valid_df[valid_df.duplicated(subset=[structure_col, endpoint_col], keep=False)]
        
        dup_count = len(duplicates)
        dup_groups = duplicates[structure_col].nunique()
        
        return {
            "exact_duplicates": dup_count,
            "duplicate_groups": dup_groups,
            "details": duplicates[[structure_col, endpoint_col]].to_dict(orient='records') if dup_count < 100 else []
        }

import pandas as pd
import numpy as np
from typing import Dict, Any, List

class StatisticsEngine:
    """
    Central analytical brain for the SDO Platform.
    Computes all counts, distributions, frequencies, histograms, and variance locally.
    Outputs clean, serialized JSON ready for the frontend WebGL charts.
    """
    
    @classmethod
    def compute_dataset_summary(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates overarching summary stats for the current dataset slice."""
        summary = {
            "total_rows": len(df),
            "total_cols": len(df.columns),
            "missing_cells": int(df.isna().sum().sum()),
            "memory_usage_mb": float(df.memory_usage(deep=True).sum() / (1024 ** 2)),
            "numeric_cols": len(df.select_dtypes(include=[np.number]).columns),
            "categorical_cols": len(df.select_dtypes(include=['object', 'category']).columns)
        }
        return summary
        
    @classmethod
    def compute_column_stats(cls, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """Calculates detailed statistics for a specific column."""
        if column not in df.columns:
            return {"error": f"Column {column} not found"}
            
        series = df[column]
        stats = {
            "name": column,
            "type": str(series.dtype),
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique())
        }
        
        if pd.api.types.is_numeric_dtype(series):
            # Numeric Stats
            stats.update({
                "mean": float(series.mean()) if not pd.isna(series.mean()) else None,
                "median": float(series.median()) if not pd.isna(series.median()) else None,
                "std": float(series.std()) if not pd.isna(series.std()) else None,
                "min": float(series.min()) if not pd.isna(series.min()) else None,
                "max": float(series.max()) if not pd.isna(series.max()) else None,
                "skewness": float(series.skew()) if not pd.isna(series.skew()) else None,
            })
            
            # Histogram bins for Distribution charts
            counts, bins = np.histogram(series.dropna(), bins='auto')
            stats["histogram"] = {
                "counts": counts.tolist(),
                "bins": bins.tolist()
            }
        else:
            # Categorical Stats - Top 50 values for Pie / Bar charts
            freq = series.value_counts(dropna=False).head(50)
            stats["frequencies"] = {
                "labels": [str(x) for x in freq.index],
                "values": freq.tolist()
            }
            
        return stats
        
    @classmethod
    def compute_correlation_matrix(cls, df: pd.DataFrame, columns: List[str] = None) -> Dict[str, Any]:
        """Calculates Pearson correlation for numeric columns."""
        if columns:
            numeric_df = df[columns].select_dtypes(include=[np.number])
        else:
            numeric_df = df.select_dtypes(include=[np.number])
            
        if numeric_df.empty:
            return {"labels": [], "matrix": []}
            
        corr = numeric_df.corr().fillna(0)
        return {
            "labels": corr.columns.tolist(),
            "matrix": corr.values.tolist()
        }


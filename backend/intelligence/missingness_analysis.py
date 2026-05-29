import pandas as pd
import plotly.express as px
from typing import Dict, Any, List

class MissingnessAnalysis:
    """Analyzes completeness of scientific datasets and generates diagnostic charts."""
    @staticmethod
    def analyze(df: pd.DataFrame, target_cols: List[str] = None) -> Dict[str, Any]:
        """Calculates missingness ratios for dataframe columns."""
        cols_to_check = target_cols if target_cols else df.columns
        cols_to_check = [c for c in cols_to_check if c in df.columns]
        
        total_rows = len(df)
        if total_rows == 0:
            return {"overall_missing_pct": 0, "column_missingness": [], "figure": None}
            
        missing_data = []
        for col in cols_to_check:
            missing_count = df[col].isna().sum()
            # Check for empty strings in object cols
            if df[col].dtype == object:
                missing_count += (df[col].astype(str).str.strip() == '').sum()
                missing_count += (df[col].astype(str).str.upper() == 'NONE').sum()
                
            pct = (missing_count / total_rows) * 100
            missing_data.append({"Column": col, "Missing %": pct, "Missing Count": missing_count})
            
        miss_df = pd.DataFrame(missing_data).sort_values("Missing %", ascending=True)
        overall_missing = miss_df['Missing %'].mean() if not miss_df.empty else 0
        
        # Premium Visualization
        fig = px.bar(miss_df, x="Missing %", y="Column", orientation='h',
                     title="Data Completeness Profile",
                     color="Missing %",
                     color_continuous_scale="Viridis",
                     template="plotly_white")
                     
        fig.update_layout(
            xaxis_title="Missingness (%)",
            yaxis_title="Features",
            margin=dict(l=20, r=20, t=40, b=20),
            height=max(400, len(miss_df) * 30)
        )
        
        return {
            "overall_missing_pct": float(overall_missing),
            "column_missingness": miss_df.to_dict(orient="records"),
            "figure": fig
        }

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("sdo.backend.utils.dataframe_optimizer")

def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimizes a pandas DataFrame by downcasting numeric datatypes
    and converting object columns with low cardinality to categories.
    
    This preserves the data while dramatically reducing memory and CPU usage
    during scientific calculations and Streamlit rendering.
    """
    if df is None or df.empty:
        return df
        
    start_mem = df.memory_usage(deep=True).sum() / (1024 * 1024)
    optimized_df = df.copy()
    
    # Identifier/specific columns that should NOT be converted to categories
    preservation_cols = {
        'canonical_smiles', 'CanonicalSMILES', 'IsomericSMILES', 
        'InChIKey', 'InChI', 'IUPACName', 'session_id', 'audit_flag',
        'PubChem_Error', 'success', 'error', 'source'
    }
    
    for col in optimized_df.columns:
        col_type = optimized_df[col].dtype
        
        # Preserve specific columns as strings/objects
        if col in preservation_cols:
            continue
            
        if pd.api.types.is_integer_dtype(col_type):
            # Downcast integers
            col_min = optimized_df[col].min()
            col_max = optimized_df[col].max()
            if col_min >= np.iinfo(np.int8).min and col_max <= np.iinfo(np.int8).max:
                optimized_df[col] = optimized_df[col].astype(np.int8)
            elif col_min >= np.iinfo(np.int16).min and col_max <= np.iinfo(np.int16).max:
                optimized_df[col] = optimized_df[col].astype(np.int16)
            elif col_min >= np.iinfo(np.int32).min and col_max <= np.iinfo(np.int32).max:
                optimized_df[col] = optimized_df[col].astype(np.int32)
            else:
                optimized_df[col] = optimized_df[col].astype(np.int64)
                
        elif pd.api.types.is_float_dtype(col_type):
            # Downcast floats to float32
            optimized_df[col] = pd.to_numeric(optimized_df[col], downcast='float')
            
        elif pd.api.types.is_object_dtype(col_type):
            # Convert object string columns to category if low cardinality
            try:
                num_unique = optimized_df[col].nunique()
                num_total = len(optimized_df)
                if num_total > 0 and (num_unique / num_total) < 0.5 and num_unique < 50:
                    optimized_df[col] = optimized_df[col].astype('category')
            except Exception:
                pass
                
    end_mem = optimized_df.memory_usage(deep=True).sum() / (1024 * 1024)
    logger.info(f"Dataframe Memory Optimization: {start_mem:.2f} MB -> {end_mem:.2f} MB ({((start_mem - end_mem)/start_mem)*100:.1f}% reduction)")
    
    return optimized_df

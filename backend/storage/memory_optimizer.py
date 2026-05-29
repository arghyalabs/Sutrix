import gc
import pandas as pd
import numpy as np
import logging
from typing import Generator, List

logger = logging.getLogger("sdo.backend.storage.memory")

def downcast_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    vectorized memory-optimization.
    Coerces float64 -> float32, and int64 -> int8/int16/int32/int64 based on value ranges.
    Converts low-cardinality string columns to category types.
    """
    if df is None or df.empty:
        return df

    optimized = df.copy()
    
    # Exclude unique descriptors and canonical SMILES keys from categorical mapping
    preservation_keys = {
        'canonical_smiles', 'CanonicalSMILES', 'IsomericSMILES', 
        'InChIKey', 'InChI', 'IUPACName', 'session_id', 'audit_flag',
        'PubChem_Error', 'success', 'error', 'source'
    }

    for col in optimized.columns:
        col_type = optimized[col].dtype
        
        if col in preservation_keys:
            continue

        if pd.api.types.is_integer_dtype(col_type):
            col_min = optimized[col].min()
            col_max = optimized[col].max()
            
            # Select narrowest integer boundary
            if col_min >= np.iinfo(np.int8).min and col_max <= np.iinfo(np.int8).max:
                optimized[col] = optimized[col].astype(np.int8)
            elif col_min >= np.iinfo(np.int16).min and col_max <= np.iinfo(np.int16).max:
                optimized[col] = optimized[col].astype(np.int16)
            elif col_min >= np.iinfo(np.int32).min and col_max <= np.iinfo(np.int32).max:
                optimized[col] = optimized[col].astype(np.int32)
            else:
                optimized[col] = optimized[col].astype(np.int64)

        elif pd.api.types.is_float_dtype(col_type):
            # Coerce default float64 to float32
            optimized[col] = pd.to_numeric(optimized[col], downcast='float')

        elif pd.api.types.is_object_dtype(col_type):
            try:
                num_unique = optimized[col].nunique()
                num_total = len(optimized)
                # If cardinality is low, convert object to Category to compress RAM size
                if num_total > 0 and (num_unique / num_total) < 0.5 and num_unique < 100:
                    optimized[col] = optimized[col].astype('category')
            except Exception:
                pass

    return optimized

def clean_memory():
    """Triggers explicit garbage collection and sweeps system caches."""
    gc.collect()

def chunked_dataframe_loader(file_path: str, chunk_size: int = 50000) -> Generator[pd.DataFrame, None, None]:
    """
    Generator pipeline that yields downcasted dataframe chunks sequentially.
    Crucial for streaming ultra-large files without spike RAM allocations.
    """
    logger.info(f"Streaming data chunk by chunk from {file_path} (Chunk Size={chunk_size})")
    
    file_ext = file_path.split('.')[-1].lower()
    
    try:
        if file_ext == 'csv':
            for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                opt_chunk = downcast_dataframe(chunk)
                yield opt_chunk
                del chunk
                gc.collect()
        elif file_ext == 'parquet':
            # Use PyArrow to read parquet files in chunks
            import pyarrow.parquet as pq
            parquet_file = pq.ParquetFile(file_path)
            for batch in parquet_file.iter_batches(batch_size=chunk_size):
                chunk_df = batch.to_pandas()
                opt_chunk = downcast_dataframe(chunk_df)
                yield opt_chunk
                del chunk_df
                gc.collect()
        else:
            # Fallback for Excel files (which cannot easily be streamed natively by pandas in chunks)
            # Load the full file but immediately downcast it
            logger.info("Excel files do not support native pandas chunking. Loading entire sheet and downcasting immediately.")
            full_df = pd.read_excel(file_path)
            opt_df = downcast_dataframe(full_df)
            yield opt_df
            del full_df
            gc.collect()
    except Exception as e:
        logger.error(f"Error encountered in memory-safe chunked loader: {e}")
        raise

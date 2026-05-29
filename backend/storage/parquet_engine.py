import os
import logging
import pandas as pd
from typing import List, Dict, Any, Optional

try:
    import pyarrow as pa
    import pyarrow.csv as pv
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False

logger = logging.getLogger("sdo.backend.storage.parquet")

class ParquetEngine:
    """
    Columnar data layer backed by Apache Arrow and Parquet.
    Eliminates redundant RAM spikes during high-throughput biological data filtering.
    """
    def __init__(self, workspace_dir: str = "uploads/parquet"):
        self.workspace_dir = os.path.abspath(workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)
        if not PYARROW_AVAILABLE:
            logger.error("PyArrow is not installed. Scientific Parquet columnar features are offline.")

    def convert_dataframe_to_parquet(self, df: pd.DataFrame, output_name: str) -> Optional[str]:
        """
        Converts an in-memory Pandas DataFrame to an optimized Parquet file using pyarrow.
        Drastically compresses file sizes and speeds up subsequent reads.
        """
        if not PYARROW_AVAILABLE:
            logger.warning("PyArrow not installed, skipping conversion.")
            # Fallback to CSV if needed? We need a path, so we can save to CSV.
            dest_path = os.path.join(self.workspace_dir, f"{output_name}.csv")
            df.to_csv(dest_path, index=False)
            return dest_path

        dest_path = os.path.join(self.workspace_dir, f"{output_name}.parquet")
        
        try:
            # Convert pandas DataFrame to Arrow Table
            table = pa.Table.from_pandas(df)
            
            # Write Table to compressed Parquet file
            pq.write_table(table, dest_path, compression='SNAPPY')
            logger.info(f"Parquet Conversion: Completed DataFrame -> {dest_path} (Snappy Compression)")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to convert DataFrame to Parquet: {e}")
            return None

    def convert_csv_to_parquet(self, csv_path: str, output_name: str) -> Optional[str]:
        """
        Converts a CSV file to an optimized Parquet file using pyarrow.
        Drastically compresses file sizes and speeds up subsequent reads.
        """
        if not PYARROW_AVAILABLE:
            logger.warning("PyArrow not installed, skipping conversion and keeping CSV source.")
            return csv_path

        dest_path = os.path.join(self.workspace_dir, f"{output_name}.parquet")
        
        try:
            # High-performance PyArrow CSV Reader (extremely fast, low-memory C implementation)
            table = pv.read_csv(csv_path)
            
            # Write Table to compressed Parquet file
            pq.write_table(table, dest_path, compression='SNAPPY')
            logger.info(f"Parquet Conversion: Completed {csv_path} -> {dest_path} (Snappy Compression)")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to convert CSV to Parquet: {e}")
            return None

    def read_columns(self, parquet_path: str, columns: List[str]) -> Optional[pd.DataFrame]:
        """
        Loads ONLY specified columns into memory.
        Crucial for loading subset features (e.g. SMILES + endpoint value) without loading 2,000+ descriptors.
        """
        if not PYARROW_AVAILABLE or not parquet_path.endswith('.parquet'):
            # Fallback for standard CSVs or if PyArrow is missing
            try:
                logger.info("PyArrow missing or file is CSV. Loading column subset via pandas fallback.")
                return pd.read_csv(parquet_path, usecols=columns)
            except Exception as e:
                logger.error(f"Fallback column-subset read failed: {e}")
                return None

        try:
            # Instant columnar loading - bypasses reading other columns entirely
            table = pq.read_table(parquet_path, columns=columns)
            return table.to_pandas()
        except Exception as e:
            logger.error(f"Failed to load Parquet columns {columns} from {parquet_path}: {e}")
            return None

    def get_row_count(self, parquet_path: str) -> int:
        """Returns the exact row count instantaneously by reading Parquet metadata."""
        if not PYARROW_AVAILABLE or not parquet_path.endswith('.parquet'):
            try:
                # Count lines without loading CSV into memory (memory-safe line counter)
                with open(parquet_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return sum(1 for _ in f) - 1 # Subtract header
            except Exception:
                return 0

        try:
            # O(1) query: reads parquet file footer metadata directly
            meta = pq.read_metadata(parquet_path)
            return meta.num_rows
        except Exception as e:
            logger.error(f"Failed to read Parquet metadata row count: {e}")
            return 0

    def get_schema(self, parquet_path: str) -> Dict[str, str]:
        """Reads database schema types directly from metadata footers."""
        schema_dict = {}
        if not PYARROW_AVAILABLE or not parquet_path.endswith('.parquet'):
            try:
                # Fallback: load first row of CSV
                df = pd.read_csv(parquet_path, nrows=1)
                for col in df.columns:
                    schema_dict[col] = str(df[col].dtype)
                return schema_dict
            except Exception:
                return {}

        try:
            schema = pq.read_schema(parquet_path)
            for name, type_ in zip(schema.names, schema.types):
                schema_dict[name] = str(type_)
            return schema_dict
        except Exception as e:
            logger.error(f"Failed to extract Parquet schema: {e}")
            return {}

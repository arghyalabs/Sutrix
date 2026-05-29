import pandas as pd
from typing import List, Tuple

class DatasetPartitionEngine:
    """
    Slices and partitions master dataframes into isolated QSAR-ready subsets based on the hierarchy.
    """
    
    @staticmethod
    def partition_recursively(df: pd.DataFrame, hierarchy_cols: List[str]) -> List[Tuple[str, pd.DataFrame]]:
        """
        Yields tuples of (path_string, dataframe) for every leaf node in the hierarchy.
        Automatically creates subdatasets.
        """
        leaf_partitions = []
        
        def recurse(current_df: pd.DataFrame, current_path: str, depth: int):
            if depth >= len(hierarchy_cols):
                # Leaf node reached (dataset fully partitioned to requested depth)
                leaf_partitions.append((current_path, current_df))
                return
                
            col = hierarchy_cols[depth]
            for group_name, group_df in current_df.groupby(col, dropna=False):
                safe_name = str(group_name).replace("/", "_").replace("\\", "_") if pd.notna(group_name) else "Unknown"
                next_path = f"{current_path}/{safe_name}" if current_path else safe_name
                recurse(group_df, next_path, depth + 1)
                
        recurse(df, "", 0)
        return leaf_partitions

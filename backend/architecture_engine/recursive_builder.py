import os
import pandas as pd
from typing import List, Tuple
import logging

logger = logging.getLogger("sdo.backend.architecture.builder")

class RecursiveBuilder:
    """
    Physically builds the recursive scientific folder architecture on the filesystem.
    """
    
    def __init__(self, base_output_dir: str):
        self.base_dir = base_output_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
    def build_architecture(self, partitions: List[Tuple[str, pd.DataFrame]], format_type: str = "csv") -> List[str]:
        """
        Takes partitioned datasets and physically generates the folder structure and files.
        Generates recursive folders and exports QSAR-ready subsets.
        """
        paths_created = []
        
        for relative_path, df in partitions:
            # Create full directory path based on recursive variables
            full_dir_path = os.path.join(self.base_dir, relative_path)
            os.makedirs(full_dir_path, exist_ok=True)
            
            # File naming based on the deepest node
            leaf_folder_name = os.path.basename(full_dir_path)
            if not leaf_folder_name:
                leaf_folder_name = "root_dataset"
                
            file_name = f"{leaf_folder_name}_qsar_ready.{format_type}"
            file_path = os.path.join(full_dir_path, file_name)
            
            # Export payload
            if format_type == "csv":
                df.to_csv(file_path, index=False)
            elif format_type == "json":
                df.to_json(file_path, orient="records")
            else:
                logger.warning(f"Unsupported export format {format_type}")
                continue
                
            paths_created.append(file_path)
            
        return paths_created

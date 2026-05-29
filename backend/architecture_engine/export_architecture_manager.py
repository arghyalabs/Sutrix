import os
import json
import logging
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any

from .ontology_router import OntologyRouter
from .hierarchy_generator import HierarchyGenerator
from .dataset_partition_engine import DatasetPartitionEngine
from .recursive_builder import RecursiveBuilder

logger = logging.getLogger("sdo.backend.architecture.manager")

class ExportArchitectureManager:
    """
    Orchestrates the entire transformation from a messy flat dataframe to a navigable, recursive computational research architecture.
    """
    def __init__(self, output_root: str = "outputs/architecture"):
        self.output_root = output_root
        if not os.path.exists(self.output_root):
            os.makedirs(self.output_root)
        
    def generate_architecture(self, df: pd.DataFrame, hierarchy: List[str], project_name: str = "QSAR_Project") -> Dict[str, Any]:
        """
        Transforms flat experimental datasets into recursive scientific folder architectures automatically.
        """
        logger.info(f"Initiating architecture generation for '{project_name}'...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = os.path.join(self.output_root, f"{project_name}_{timestamp}")
        
        # 1. Validate Ontology Routing
        valid_hierarchy = OntologyRouter.validate_hierarchy(df.columns.tolist(), hierarchy)
        if not valid_hierarchy and hierarchy:
            return {"success": False, "error": "No valid hierarchy variables found in the dataset."}
            
        # 2. Generate Abstract Hierarchy Tree (Visualizations)
        tree_preview = HierarchyGenerator.generate_preview_tree(df, valid_hierarchy)
        tree_string = HierarchyGenerator.format_tree_string(tree_preview)
        
        # 3. Partition the Dataset
        partitions = DatasetPartitionEngine.partition_recursively(df, valid_hierarchy)
        
        # 4. Physically Build the Recursive Architecture and export QSAR subsets
        builder = RecursiveBuilder(project_dir)
        exported_files = builder.build_architecture(partitions, format_type="csv")
        
        # 5. Generate Metadata & Workflow Lineage Report
        self._generate_metadata_report(project_dir, tree_string, valid_hierarchy, exported_files)
        
        logger.info(f"Architecture generated successfully at {project_dir}")
        return {
            "success": True,
            "project_dir": project_dir,
            "tree": tree_preview,
            "tree_string": tree_string,
            "partitions_created": len(exported_files),
            "files": exported_files
        }
        
    def _generate_metadata_report(self, project_dir: str, tree_string: str, hierarchy: List[str], files: List[str]):
        """Generates the workflow lineage view and architecture metadata report."""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "workflow_lineage": "Flat Dataset -> Subdataset Partitioning -> Recursive Building -> QSAR Ready Export",
            "hierarchy_routing": hierarchy,
            "total_partitions": len(files),
            "files_generated": files
        }
        
        # Write JSON metadata
        with open(os.path.join(project_dir, "architecture_metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)
            
        # Write text-based scientific architecture map (collapsible view text representation)
        with open(os.path.join(project_dir, "scientific_architecture_map.txt"), "w", encoding='utf-8') as f:
            f.write("====================================================\n")
            f.write("         RECURSIVE SCIENTIFIC ARCHITECTURE          \n")
            f.write("====================================================\n\n")
            
            f.write("WORKFLOW LINEAGE:\n")
            f.write(" [Raw Experimental Data] -> [Ontology Routing] -> [Recursive Partitioning] -> [QSAR Subsets]\n\n")
            
            f.write("HIERARCHY PATH:\n")
            f.write(" -> ".join(hierarchy) if hierarchy else "Flat Output")
            f.write("\n\n")
            
            f.write("ARCHITECTURE MAP (PREVIEW):\n")
            f.write(tree_string)

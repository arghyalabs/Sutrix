from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import pandas as pd
import json
from datetime import datetime
import re
import io

@dataclass
class SegregationNode:
    """Represents a node in the segregation hierarchy."""
    level: int
    variable: str
    value: str
    data: pd.DataFrame
    children: List['SegregationNode'] = field(default_factory=list)
    path: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class SegregationResult:
    """Result of segregation operation."""
    root_path: str
    total_folders: int
    total_files: int
    hierarchy_levels: int
    leaf_nodes: List[dict]
    statistics: dict
    variance_summary: Optional[Any] = None

class HierarchicalSegregationEngine:
    """Core engine for hierarchical dataset segregation."""
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def build_hierarchy_tree(self, df: pd.DataFrame, 
                             hierarchy: List[str], 
                             level: int = 0, 
                             current_path: str = "",
                             current_tags: Dict[str, str] = None) -> SegregationNode:
        """
        Recursively build a hierarchy tree from dataframe.
        """
        if current_tags is None:
            current_tags = {}
            
        root = SegregationNode(
            level=level,
            variable="root" if level == 0 else "node",
            value="all",
            data=df,
            path=current_path,
            tags=current_tags.copy()
        )
        
        if not hierarchy:
            return root
        
        current_var = hierarchy[0]
        remaining_hierarchy = hierarchy[1:]
        
        # Group by current hierarchy level
        if current_var not in df.columns:
            # Skip missing hierarchy levels
            if remaining_hierarchy:
                return self.build_hierarchy_tree(df, remaining_hierarchy, level, current_path, current_tags)
            return root
        
        # Ensure column used for grouping exists and handle NaNs gracefully
        grouped = df.groupby(current_var, dropna=False)
        
        for group_value, group_df in grouped:
            safe_value = self._sanitize_folder_name(str(group_value), current_var)
            new_path = f"{current_path}/{safe_value}" if current_path else safe_value
            
            new_tags = current_tags.copy()
            new_tags[current_var] = str(group_value) if not pd.isna(group_value) else f"Uncategorized_{current_var}"
            
            child_node = SegregationNode(
                level=level + 1,
                variable=current_var,
                value=str(group_value),
                data=group_df,
                path=new_path,
                tags=new_tags
            )
            
            if remaining_hierarchy:
                child_tree = self.build_hierarchy_tree(group_df, remaining_hierarchy, level + 1, new_path, new_tags)
                child_node.children.extend(child_tree.children)
            
            root.children.append(child_node)
        
        return root
    
    # Human-readable labels for qualifier symbols that would otherwise become
    # meaningless after filesystem-illegal characters are stripped.
    _QUALIFIER_LABELS = {
        '>':    'Greater_Than',
        '<':    'Less_Than',
        '>=':   'Greater_Than_Or_Equal',
        '<=':   'Less_Than_Or_Equal',
        '=':    'Exact',
        '~':    'Approximate',
        'ca.':  'Approximate',
        'ND':   'Not_Detected',
        '<LOD': 'Below_LOD',
        '>LOQ': 'Above_LOQ',
    }

    def _sanitize_folder_name(self, name: str, variable_name: str = "Variable") -> str:
        """Sanitize string for use as folder name."""
        if pd.isna(name) or str(name).lower() in ('nan', 'none', 'null', '<na>', ''):
            return "nan"
        
        raw = str(name).strip()
        
        # Map known qualifier symbols to human-readable labels
        if raw in self._QUALIFIER_LABELS:
            return self._QUALIFIER_LABELS[raw]
            
        # Replace invalid characters with underscore
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', raw)
        # Truncate long names to prevent OS path length issues
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        return safe_name.strip('. ')
    
    def generate_folders(self, root: SegregationNode, 
                         base_path: Path,
                         export_format: str = 'xlsx',
                         column_mappings: Optional[dict] = None) -> Tuple[int, int, List[dict]]:
        """
        Recursively generate folder structure and export files.
        
        Args:
            root: Root node of hierarchy tree
            base_path: Base output directory
            export_format: Output file format (xlsx, csv)
            column_mappings: Optional dict mapping user columns to scientific variables
            
        Returns:
            Tuple of (total_folders, total_files, leaf_node_info)
        """
        total_folders = 0
        total_files = 0
        leaf_nodes = []
        
        if not root.children:
            # Leaf node - export data
            if not root.data.empty:
                df = root.data
                
                # Apply local file-by-file log10 variance audit
                variance_summary = None
                if column_mappings:
                    from backend.processing.auditor import ScientificAuditor
                    auditor = ScientificAuditor()
                    # compute_variance_flags computes the log10 range locally and appends the 'audit_flag'
                    flagged_df, variance_summary = auditor.compute_variance_flags(df, column_mappings)
                    df = flagged_df
                
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if export_format == 'xlsx':
                    filename = f"data_{timestamp}.xlsx"
                else:
                    filename = f"data_{timestamp}.csv"
                
                # Write to BytesIO buffer instead of disk
                buffer = io.BytesIO()
                if export_format == 'xlsx':
                    df.to_excel(buffer, index=False, engine='xlsxwriter')
                else:
                    csv_data = df.to_csv(index=False)
                    buffer.write(csv_data.encode('utf-8'))
                buffer.seek(0)
                
                total_files += 1
                if root.path and root.path != "all":
                    total_folders += 1
                
                rel_path = root.path if root.path and root.path != "all" else ""
                
                leaf_nodes.append({
                    'path': rel_path,
                    'filename': filename,
                    'records': len(df),
                    'compounds': df.iloc[:, 0].nunique() if len(df.columns) > 0 else 0,
                    'buffer': buffer,
                    'hierarchy_tags': root.tags,
                    'df': df,
                    'variance_summary': variance_summary
                })
        else:
            # Non-leaf node - process children
            for child in root.children:
                # the child.path handles the recursive path string, so base_path stays the same
                sub_folders, sub_files, sub_leaves = self.generate_folders(
                    child, base_path, export_format, column_mappings
                )
                total_folders += sub_folders
                total_files += sub_files
                leaf_nodes.extend(sub_leaves)
            
            # Only count as folder if it's not the top "all" wrapper
            if root.path and root.path != "all":
                total_folders += 1
                
        return total_folders, total_files, leaf_nodes
    
    def segregate(self, df: pd.DataFrame, 
                  hierarchy: List[str],
                  output_dir: Optional[str] = None,
                  export_format: str = 'xlsx',
                  session_id: Optional[str] = None,
                  column_mappings: Optional[dict] = None) -> SegregationResult:
        """
        Main segregation method.
        
        Args:
            df: Input dataframe
            hierarchy: List of column names for hierarchy
            output_dir: Output directory (default: outputs/segregation_{session_id})
            export_format: Output file format
            session_id: Optional session identifier
            column_mappings: Optional dict mapping user columns to scientific variables
            
        Returns:
            SegregationResult with all metadata
        """
        if output_dir is None:
            output_dir = "Root"
        
        # We don't create directories anymore since we use BytesIO
        
        # Build hierarchy tree
        root = self.build_hierarchy_tree(df, hierarchy)
        
        # Generate folders and export files
        total_folders, total_files, leaf_nodes = self.generate_folders(
            root, None, export_format, column_mappings
        )
        
        # Calculate statistics
        statistics = {
            'input_records': len(df),
            'input_columns': len(df.columns),
            'hierarchy_levels': len(hierarchy),
            'hierarchy_variables': hierarchy,
            'output_folders': total_folders,
            'output_files': total_files,
            'leaf_nodes': len(leaf_nodes),
            'avg_records_per_file': len(df) / max(total_files, 1),
            'min_records_per_file': min((ln['records'] for ln in leaf_nodes), default=0),
            'max_records_per_file': max((ln['records'] for ln in leaf_nodes), default=0)
        }
        
        # Aggregate local variance summaries from leaf nodes
        combined_consistent = 0
        combined_moderate = 0
        combined_conflict = 0
        combined_conflict_compounds = []
        combined_total_groups = 0
        
        has_variance = False
        for leaf in leaf_nodes:
            vs = leaf.get('variance_summary')
            if vs is not None:
                has_variance = True
                combined_consistent += vs.consistent_count
                combined_moderate += vs.moderate_count
                combined_conflict += vs.conflict_count
                combined_conflict_compounds.extend(vs.conflict_compounds)
                combined_total_groups += vs.total_groups_analyzed
                
        if has_variance:
            from backend.processing.auditor import VarianceSummary
            passed = combined_consistent + combined_moderate
            score = (passed / combined_total_groups * 100.0) if combined_total_groups > 0 else 100.0
            
            aggregated_vs = VarianceSummary(
                consistent_count=combined_consistent,
                moderate_count=combined_moderate,
                conflict_count=combined_conflict,
                conflict_compounds=combined_conflict_compounds[:50],
                consistency_score=round(score, 1),
                total_groups_analyzed=combined_total_groups
            )
        else:
            aggregated_vs = None
            
        return SegregationResult(
            root_path=output_dir,
            total_folders=total_folders,
            total_files=total_files,
            hierarchy_levels=len(hierarchy),
            leaf_nodes=leaf_nodes,
            statistics=statistics,
            variance_summary=aggregated_vs
        )

import pandas as pd
from typing import List, Dict, Any

class HierarchyGenerator:
    """
    Builds the recursive scientific architecture tree from a flat dataframe.
    """
    
    @staticmethod
    def generate_preview_tree(df: pd.DataFrame, hierarchy_cols: List[str]) -> Dict[str, Any]:
        """
        Generates an abstract syntax tree (AST) like structure of the dataset.
        Returns a nested dictionary representing the collapsible scientific architecture and record counts.
        """
        if not hierarchy_cols:
            return {"name": "Root Dataset", "count": len(df), "children": []}

        def build_tree(current_df: pd.DataFrame, depth: int) -> List[Dict[str, Any]]:
            if depth >= len(hierarchy_cols) or current_df.empty:
                return []
                
            current_col = hierarchy_cols[depth]
            children = []
            
            # Group by current hierarchy level
            for group_name, group_df in current_df.groupby(current_col, dropna=False):
                # Clean group name for filesystem usage
                safe_name = str(group_name).replace("/", "_").replace("\\", "_") if pd.notna(group_name) else "Unknown"
                
                node = {
                    "name": safe_name,
                    "level": current_col,
                    "count": len(group_df),
                    "children": build_tree(group_df, depth + 1)
                }
                children.append(node)
                
            return children

        return {
            "name": "Root Dataset",
            "count": len(df),
            "children": build_tree(df, 0)
        }
        
    @staticmethod
    def format_tree_string(tree: Dict[str, Any], indent: str = "") -> str:
        """Generates a text-based hierarchy preview tree (Visualizer)."""
        res = f"{indent}📁 {tree['name']} (n={tree.get('count', 0)})\n"
        for i, child in enumerate(tree.get('children', [])):
            is_last = (i == len(tree['children']) - 1)
            prefix = "└── " if is_last else "├── "
            child_indent = indent + ("    " if is_last else "│   ")
            
            # Recursively print children
            res += f"{indent}{prefix}📁 {child['name']} [{child['level']}] (n={child.get('count', 0)})\n"
            for grandchild in child.get('children', []):
                res += HierarchyGenerator.format_tree_string(grandchild, child_indent)
        return res

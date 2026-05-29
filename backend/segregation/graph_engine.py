import os
import time
import hashlib
from typing import List, Dict, Any, Optional
import pandas as pd
import networkx as nx

class DAGSegregationEngine:
    """
    Replaces the primitive folder-based hierarchy with a robust Directed Acyclic Graph (DAG) 
    using NetworkX to support branch recombination, reversible filtering, and lineage tracking.
    """
    
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.graph = nx.DiGraph()
        
    def _generate_node_id(self, parent_id: str, level_name: str, level_value: str) -> str:
        """Generates a reproducible SHA256 hash for the node."""
        raw_str = f"{parent_id}|{level_name}|{level_value}"
        return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()[:12]

    def build_dag(self, df: pd.DataFrame, hierarchy: List[str]) -> nx.DiGraph:
        """
        Builds the directed acyclic graph based on the selected hierarchy.
        """
        # Create Root Node
        root_id = "root"
        self.graph.add_node(
            root_id, 
            level=0, 
            name="Root", 
            value="All Data",
            count=len(df),
            filters={},
            path="Root"
        )
        
        if not hierarchy:
            return self.graph
            
        self._build_edges(df, hierarchy, 0, root_id, {})
        return self.graph

    def _build_edges(self, 
                     df: pd.DataFrame, 
                     hierarchy: List[str], 
                     level: int, 
                     parent_id: str, 
                     current_filters: Dict[str, str]):
        """Recursively builds edges and nodes by grouping."""
        if not hierarchy:
            return
            
        current_var = hierarchy[0]
        remaining_vars = hierarchy[1:]
        
        if current_var not in df.columns:
            # Skip if column doesn't exist
            if remaining_vars:
                self._build_edges(df, remaining_vars, level, parent_id, current_filters)
            return
            
        grouped = df.groupby(current_var, dropna=False)
        
        for group_val, group_df in grouped:
            val_str = str(group_val) if not pd.isna(group_val) else f"Uncategorized_{current_var}"
            
            node_id = self._generate_node_id(parent_id, current_var, val_str)
            
            new_filters = current_filters.copy()
            new_filters[current_var] = val_str
            
            parent_path = self.graph.nodes[parent_id]["path"]
            node_path = f"{parent_path} > {val_str}"
            
            # Add node
            self.graph.add_node(
                node_id,
                level=level + 1,
                name=current_var,
                value=val_str,
                count=len(group_df),
                filters=new_filters,
                path=node_path
            )
            
            # Add directed edge from parent to child
            self.graph.add_edge(parent_id, node_id, filter_col=current_var, filter_val=val_str)
            
            # Recursively build deeper levels
            if remaining_vars:
                self._build_edges(group_df, remaining_vars, level + 1, node_id, new_filters)
                
    def export_graph_data(self) -> Dict[str, Any]:
        """Exports the DAG into a serializable JSON dictionary for the frontend."""
        nodes = []
        for n, attrs in self.graph.nodes(data=True):
            node_data = {"id": n}
            node_data.update(attrs)
            nodes.append(node_data)
            
        edges = []
        for u, v, attrs in self.graph.edges(data=True):
            edge_data = {"source": u, "target": v}
            edge_data.update(attrs)
            edges.append(edge_data)
            
        return {
            "nodes": nodes,
            "edges": edges,
            "root_id": "root",
            "total_nodes": len(self.graph.nodes),
            "max_depth": max((nx.shortest_path_length(self.graph, "root", n) for n in self.graph.nodes), default=0)
        }

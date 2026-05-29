from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from typing import List, Optional, Callable
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

from backend.segregation.engine import HierarchicalSegregationEngine, SegregationResult

def _process_subtree(engine: HierarchicalSegregationEngine, df: pd.DataFrame, 
                     hierarchy: List[str], base_path_str: str, 
                     export_format: str, initial_tags: dict):
    """
    Standalone function to process a subtree for multiprocessing.
    Must be top-level to be picklable by ProcessPoolExecutor.
    """
    root = engine.build_hierarchy_tree(
        df=df, 
        hierarchy=hierarchy, 
        level=1, 
        current_path=base_path_str,
        current_tags=initial_tags
    )
    base_path = Path(base_path_str)
    
    # We do not want to create an "all" folder in the subtree if it shouldn't exist, 
    # but the hierarchy has already advanced. 
    # The parent logic will set the correct subpath in the df if needed.
    return engine.generate_folders(root, base_path, export_format)

def _process_leaf_chunk(chunk_tasks: List[dict], 
                       export_format: str,
                       column_mappings: Optional[dict] = None) -> List[dict]:
    """
    Process a chunk of leaf nodes sequentially inside a worker process.
    """
    import io
    from datetime import datetime
    import pandas as pd
    from backend.processing.auditor import ScientificAuditor
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = []
    
    for task in chunk_tasks:
        df = task['df']
        path = task['path']
        tags = task['tags']
        
        # Apply local file-by-file log10 variance audit
        variance_summary = None
        if column_mappings:
            auditor = ScientificAuditor()
            # compute_variance_flags computes the log10 range locally and appends the 'audit_flag'
            flagged_df, variance_summary = auditor.compute_variance_flags(df, column_mappings)
            df = flagged_df
            
        if export_format == 'xlsx':
            filename = f"data_{timestamp}.xlsx"
        else:
            filename = f"data_{timestamp}.csv"
            
        buffer = io.BytesIO()
        if export_format == 'xlsx':
            df.to_excel(buffer, index=False, engine='xlsxwriter')
        else:
            csv_data = df.to_csv(index=False)
            buffer.write(csv_data.encode('utf-8'))
        buffer.seek(0)
        
        results.append({
            'path': path,
            'filename': filename,
            'records': len(df),
            'compounds': df.iloc[:, 0].nunique() if len(df.columns) > 0 else 0,
            'buffer': buffer,
            'hierarchy_tags': tags,
            'df': df,
            'variance_summary': variance_summary
        })
        
    return results

class OptimizedSegregationEngine(HierarchicalSegregationEngine):
    """Optimized segregation engine with parallel processing."""
    
    def __init__(self, output_dir: str = "outputs", 
                 max_workers: int = None,
                 chunk_size: int = 10000):
          super().__init__(output_dir)
          self.max_workers = max_workers or multiprocessing.cpu_count()
          self.chunk_size = chunk_size
    
    def segregate_parallel(self, df: pd.DataFrame,
                           hierarchy: List[str],
                           output_dir: Optional[str] = None,
                           export_format: str = 'xlsx',
                           session_id: Optional[str] = None,
                           progress_callback: Optional[Callable[[int, int], None]] = None,
                           column_mappings: Optional[dict] = None) -> SegregationResult:
        """Parallel segregation using fully chunked leaf node execution."""
        if not hierarchy:
            return self.segregate(df, hierarchy, output_dir, export_format, session_id, column_mappings)
            
        if output_dir is None:
            output_dir = "Root"
            
        # Group by the entire hierarchy list to get all leaf nodes directly
        # This is incredibly fast (under 0.1 seconds in pandas)
        grouped = df.groupby(hierarchy, dropna=False)
        
        tasks = []
        for group_key, group_df in grouped:
            if group_df.empty:
                continue
                
            # If hierarchy has only 1 variable, group_key is a single value instead of a tuple
            if len(hierarchy) == 1:
                key_tuple = (group_key,)
            else:
                key_tuple = group_key
                
            # Construct sanitize path
            path_parts = []
            tags = {}
            for val, var in zip(key_tuple, hierarchy):
                safe_val = self._sanitize_folder_name(str(val), var)
                path_parts.append(safe_val)
                tags[var] = str(val) if not pd.isna(val) else f"Uncategorized_{var}"
                
            path_str = "/".join(path_parts)
            
            tasks.append({
                'df': group_df,
                'path': path_str,
                'tags': tags
            })
            
        if not tasks:
            return self.segregate(df, hierarchy, output_dir, export_format, session_id, column_mappings)
            
        # Partition tasks into chunks for workers
        num_workers = min(self.max_workers, len(tasks))
        chunks = [[] for _ in range(num_workers)]
        for idx, task in enumerate(tasks):
            chunks[idx % num_workers].append(task)
            
        leaf_nodes = []
        futures = {}
        
        try:
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                for i, chunk in enumerate(chunks):
                    if not chunk:
                        continue
                    future = executor.submit(
                        _process_leaf_chunk,
                        chunk,
                        export_format,
                        column_mappings
                    )
                    futures[future] = len(chunk)
                    
                total_groups = len(futures)
                completed_count = 0
                
                for future in as_completed(futures):
                    chunk_size = futures[future]
                    try:
                        chunk_results = future.result()
                        leaf_nodes.extend(chunk_results)
                    except Exception as exc:
                        print(f"Leaf chunk processing generated an exception: {exc}")
                    finally:
                        completed_count += 1
                        if progress_callback:
                            progress_callback(completed_count, total_groups)
        except Exception as pe:
            print(f"Failed to execute ProcessPoolExecutor, falling back to sequential: {pe}")
            leaf_nodes = []
            non_empty_chunks = [c for c in chunks if c]
            total_groups = len(non_empty_chunks)
            completed_count = 0
            for chunk in non_empty_chunks:
                try:
                    chunk_results = _process_leaf_chunk(chunk, export_format, column_mappings)
                    leaf_nodes.extend(chunk_results)
                except Exception as exc:
                    print(f"Sequential leaf chunk processing generated an exception: {exc}")
                finally:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, total_groups)
                        
        # Calculate unique folders using prefix paths
        unique_folders = set()
        for leaf in leaf_nodes:
            path_str = leaf['path']
            if path_str:
                parts = path_str.split('/')
                for j in range(1, len(parts) + 1):
                    unique_folders.add("/".join(parts[:j]))
                    
        total_folders = len(unique_folders)
        total_files = len(leaf_nodes)
        
        statistics = {
            'input_records': len(df),
            'input_columns': len(df.columns),
            'hierarchy_levels': len(hierarchy),
            'hierarchy_variables': hierarchy,
            'output_folders': total_folders,
            'output_files': total_files,
            'leaf_nodes': len(leaf_nodes),
            'avg_records_per_file': len(df) / max(total_files, 1),
            'min_records_per_file': min((ln['records'] for ln in leaf_nodes), default=0) if leaf_nodes else 0,
            'max_records_per_file': max((ln['records'] for ln in leaf_nodes), default=0) if leaf_nodes else 0
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

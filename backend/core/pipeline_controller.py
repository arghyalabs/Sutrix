# -----------------------------------------------------------------------------
# Scientific Data Orchestrator (SDO)
# Copyright (c) 2026. All Rights Reserved.
# Licensed under the PolyForm Noncommercial License 1.0.0.
# -----------------------------------------------------------------------------
import logging
import pandas as pd
from typing import Dict, Any, List

from backend.core.workspace_registry import PipelineContext
from backend.utils.file_handler import FileIngestionEngine
from backend.storage.parquet_engine import ParquetEngine
from backend.storage.memory_optimizer import downcast_dataframe, clean_memory
from backend.workers.task_manager import TaskManager
from backend.processing.readiness_engine import DatasetReadinessScorer, ScientificIntelligenceEngine

logger = logging.getLogger("sdo.core.pipeline")
parquet_engine = ParquetEngine()

class ScientificPipelineController:
    """Single Source of Truth for Scientific Orchestration Sequence."""
    
    VALID_TRANSITIONS = {
        "ingest": [],
        "mapping": ["ingest"],
        "segregate": ["mapping"],
        "enrich": ["mapping", "segregate"],
        "readiness": ["enrich"]
    }

    @staticmethod
    def validate_stage_transition(context: PipelineContext, requested_stage: str):
        """Deterministic stage ordering validation."""
        required_stages = ScientificPipelineController.VALID_TRANSITIONS.get(requested_stage, [])
        for req in required_stages:
            if req not in context.execution_trace:
                raise ValueError(f"Scientific violation: Cannot execute '{requested_stage}' before '{req}'")

    @staticmethod
    async def ingest_dataset(context: PipelineContext, filename: str, temp_path: str, file_bytes: bytes) -> Dict[str, Any]:
        async with context._lock:
            ScientificPipelineController.validate_stage_transition(context, "ingest")

            import asyncio
            loop = asyncio.get_running_loop()
            workspace_id = context.workspace_id  # snapshot before thread

            def _do_ingest():
                engine = FileIngestionEngine()
                result = engine.ingest(temp_path, file_bytes=file_bytes)
                if not result.success or result.primary_df is None:
                    raise ValueError(" | ".join(result.errors))
                optimized_df = downcast_dataframe(result.primary_df)
                parquet_path = parquet_engine.convert_dataframe_to_parquet(optimized_df, f"ingested_{workspace_id}")
                row_count = len(optimized_df)
                col_names = list(optimized_df.columns)
                preview_data = optimized_df.head(10).fillna("").to_dict(orient="records")
                return optimized_df, parquet_path, row_count, col_names, preview_data

            optimized_df, parquet_path, row_count, col_names, preview_data = await loop.run_in_executor(None, _do_ingest)

            # Apply context mutations on the async side (never inside thread)
            context.parquet_path = parquet_path
            context.dataframe_cache = optimized_df
            context.add_trace("ingest")
            context.add_snapshot("ingest", parquet_path, {"rows": row_count, "cols": len(col_names)})
            # Skip clean_memory() on small datasets — not needed, adds latency

            return {
                "success": True,
                "filename": filename,
                "row_count": row_count,
                "columns": col_names,
                "preview": preview_data,
                "parquet_path": parquet_path
            }

    @staticmethod
    async def curate_columns(context: PipelineContext, columns_to_drop: List[str]) -> Dict[str, Any]:
        async with context._lock:
            import asyncio
            loop = asyncio.get_running_loop()

            # Snapshot inputs before entering thread
            current_path = context.parquet_path
            current_df = context.dataframe_cache
            workspace_id = context.workspace_id

            def _do_curate():
                # Load df from cache or parquet
                if current_df is not None:
                    df = current_df
                elif current_path and os.path.exists(current_path):
                    import pandas as pd
                    df = pd.read_parquet(current_path)
                else:
                    raise ValueError(f"No parquet source for {workspace_id}")

                dropped = False
                new_path = current_path
                if columns_to_drop:
                    cols_existing = [c for c in columns_to_drop if c in df.columns]
                    if cols_existing:
                        df = df.drop(columns=cols_existing)
                        new_path = parquet_engine.convert_dataframe_to_parquet(df, f"curated_{workspace_id}")
                        dropped = True
                return (
                    df,
                    new_path,
                    dropped,
                    len(df),
                    list(df.columns),
                    df.head(10).fillna("").to_dict(orient="records"),
                )

            df, new_path, dropped, row_count, col_names, preview_data = await loop.run_in_executor(None, _do_curate)

            # Apply context mutations on the async side (thread-safe)
            if dropped:
                context.parquet_path = new_path
                context.dataframe_cache = df
                context.add_trace("curate")

            return {
                "success": True,
                "row_count": row_count,
                "columns": col_names,
                "preview": preview_data,
                "parquet_path": new_path,
            }

    @staticmethod
    async def apply_column_mapping(context: PipelineContext, mappings: Dict[str, str]) -> Dict[str, Any]:
        async with context._lock:
            ScientificPipelineController.validate_stage_transition(context, "mapping")
            import asyncio
            loop = asyncio.get_running_loop()

            # Snapshot thread-safe inputs
            current_path = context.parquet_path
            current_df = context.dataframe_cache
            workspace_id = context.workspace_id

            def _do_mapping():
                if current_df is not None:
                    df = current_df.copy()  # copy needed since we mutate
                elif current_path and os.path.exists(current_path):
                    import pandas as pd
                    df = pd.read_parquet(current_path)
                else:
                    raise ValueError(f"No parquet source for {workspace_id}")

                final_mappings = mappings.copy()
                new_path = current_path

                val_col = next((k for k, v in mappings.items() if v == 'value'), None)
                if val_col and val_col in df.columns:
                    from backend.utils.qualifier_parser import QualifierParser
                    parser = QualifierParser()

                    q_vals, q_quals, q_units, q_qsar = [], [], [], []
                    for val in df[val_col]:
                        res = parser.parse(val)
                        if res:
                            q_vals.append(res.value)
                            q_quals.append(res.qualifier.value if res.qualifier else None)
                            q_units.append(res.unit)
                            q_qsar.append(res.qsar_ready)
                        else:
                            q_vals.append(float('nan'))
                            q_quals.append(None)
                            q_units.append("")
                            q_qsar.append(False)

                    df[f"{val_col}_numeric"] = q_vals
                    df[f"{val_col}_qualifier"] = q_quals
                    df[f"{val_col}_unit"] = q_units
                    df[f"{val_col}_qsar_ready"] = q_qsar

                    final_mappings[f"{val_col}_numeric"] = 'value'
                    final_mappings[f"{val_col}_qualifier"] = 'qualifier'
                    if not any(v == 'unit' for v in mappings.values()):
                        final_mappings[f"{val_col}_unit"] = 'unit'
                    final_mappings[val_col] = 'none'

                    from backend.core.scientific_runtime import ScientificRuntime
                    smiles_col = next((k for k, v in final_mappings.items() if v in ['canonical_smiles', 'smiles']), None)
                    if smiles_col and smiles_col in df.columns:
                        df[smiles_col] = df[smiles_col].astype(str).apply(ScientificRuntime.canonicalize_smiles)

                    new_path = parquet_engine.convert_dataframe_to_parquet(df, f"mapped_{workspace_id}")

                from backend.core.ecotox.ecotox_classifier import EcotoxClassifier
                dataset_type = EcotoxClassifier.classify_dataset_type(list(df.columns), final_mappings)
                warnings = EcotoxClassifier.validate_toxicological_safety(final_mappings, list(df.columns))

                return df, new_path, final_mappings, list(df.columns), dataset_type, warnings

            df, new_path, final_mappings, col_names, dataset_type, warnings = await loop.run_in_executor(None, _do_mapping)

            # Apply ALL context mutations on the async side
            context.parquet_path = new_path
            context.dataframe_cache = df
            context.mappings = final_mappings
            context.add_trace("mapping")  # THIS is what was missing

            return {
                "success": True,
                "mappings": final_mappings,
                "columns": col_names,
                "dataset_type": dataset_type,
                "warnings": warnings,
            }

    @staticmethod
    async def perform_segmentation(
        context: PipelineContext,
        enable_dedup: bool = False,
        enable_variance_pruning: bool = False,
        prune_high_variance: bool = False,
        selected_hierarchy: List[str] = None
    ) -> str:
        """Dispatches the graph building task asynchronously to the background worker."""
        async with context._lock:
            ScientificPipelineController.validate_stage_transition(context, "segregate")
            df = context.load_slice()
            
            # Derive hierarchy from mapped columns if none provided
            if not selected_hierarchy:
                available_variables = [col for col in context.mappings if col in df.columns]
                desired_sci_order = ['study_type', 'toxicity_category', 'species', 'endpoint', 'qualifier', 'duration']
                sci_to_user = {v: k for k, v in context.mappings.items() if k in available_variables}
                default_hierarchy = []
                for sci_var in desired_sci_order:
                    if sci_var in sci_to_user:
                        default_hierarchy.append(sci_to_user[sci_var])
                selected_hierarchy = default_hierarchy if default_hierarchy else available_variables[:2]
                
            from backend.workers.task_manager import TaskManager
            job_id = TaskManager.submit_segregation(
                context_id=context.workspace_id,
                df=df,
                hierarchy=selected_hierarchy,
                enable_dedup=enable_dedup,
                enable_variance_pruning=enable_variance_pruning,
                prune_high_variance=prune_high_variance
            )
            
            context.active_hierarchy = selected_hierarchy
            context.active_job_id = job_id
            context.add_trace(f"queued_segregation_job_{job_id}")
            return job_id



    @staticmethod
    async def run_enrichment(context: PipelineContext, selected_descriptors: List[str], include_mordred: bool, mode: str) -> str:
        async with context._lock:
            ScientificPipelineController.validate_stage_transition(context, "enrich")
            df = context.load_slice()
            
            job_id = TaskManager.submit_enrichment(
                df=df,
                mappings=context.mappings,
                selected_descriptors=selected_descriptors,
                include_mordred=include_mordred,
                mode=mode,
                workspace_id=context.workspace_id
            )
            
            if not job_id:
                raise ValueError("Failed to initialize computational task in registry.")
            
            context.active_job_id = job_id
            context.add_trace("enrich")
            context.flush_memory()
            return job_id

    @staticmethod
    async def assemble_enrichment_result(context: PipelineContext) -> Dict[str, Any]:
        async with context._lock:
            if not context.active_job_id:
                raise ValueError("No active job found in workspace.")
                
            status = TaskManager.query_status(context.active_job_id)
            if status["status"] != "COMPLETED":
                raise ValueError(f"Job results unavailable. Status: {status['status']}")
                
            res_path = status["result_path"]
            if res_path == "Lineage Engine":
                raise ValueError("Enriched output parquet file not found. The active job appears to be a segregation job. Please re-run enrichment.")
            elif not res_path:
                raise ValueError("Enriched output parquet file not found. The job completed but no result path was saved. This can happen if no resolvable compounds were found in the dataset.")
                
            # Update source of truth to the new enriched parquet
            context.parquet_path = res_path
            context.add_snapshot("enrich", res_path, {"job_id": context.active_job_id})
            
            df = context.load_slice()
            
            # Re-package segregated files with the enriched dataframe in the background (prevents blocking the API response)
            if context.active_lineage and context.active_hierarchy:
                from backend.core.lineage_builder import LineageBuilder
                import asyncio
                import logging
                
                async def rebuild_lineage_background(df_copy):
                    try:
                        loop = asyncio.get_running_loop()
                        lineage_data = await loop.run_in_executor(
                            None,
                            lambda: LineageBuilder.run(
                                df=df_copy,
                                hierarchy_cols=context.active_hierarchy,
                                mappings=context.mappings,
                                workspace_id=context.workspace_id,
                                broadcast_fn=None
                            )
                        )
                        async with context._lock:
                            context.active_lineage = lineage_data
                            context.hierarchy_engine = lineage_data.get("_engine")
                            context.active_segregation_result = lineage_data
                        logging.getLogger("sdo.backend.core.pipeline_controller").info("Lineage successfully rebuilt in background after enrichment.")
                    except Exception as e:
                        logging.getLogger("sdo.backend.core.pipeline_controller").error(f"Failed to rebuild lineage in background after enrichment: {e}")

                asyncio.create_task(rebuild_lineage_background(df.copy()))
            
            preview = df.head(100).fillna("").to_dict(orient="records")
            
            return {
                "job_id": context.active_job_id,
                "total_rows": len(df),
                "columns": list(df.columns),
                "preview": preview,
                "parquet_path": res_path
            }

    @staticmethod
    async def run_readiness_analysis(context: PipelineContext) -> Dict[str, Any]:
        async with context._lock:
            ScientificPipelineController.validate_stage_transition(context, "readiness")
            import asyncio
            loop = asyncio.get_running_loop()

            def _do_readiness():
                df = context.load_slice()
                scorer = DatasetReadinessScorer()
                drs_res = scorer.evaluate(df, context.mappings)
                harmonization_res = ScientificIntelligenceEngine.audit_endpoint_harmonization(df, context.mappings)
                return {
                    "score": drs_res["score"],
                    "tier": drs_res["tier"],
                    "breakdown": drs_res["breakdown"],
                    "deductions": drs_res["deductions"],
                    "harmonized": harmonization_res["harmonized"],
                    "findings": harmonization_res["findings"],
                }

            results = await loop.run_in_executor(None, _do_readiness)
            context.readiness_results = results
            context.add_trace("readiness")
            context.flush_memory()
            return results


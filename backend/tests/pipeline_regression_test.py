import os
import time
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from backend.core.workspace_registry import registry
from backend.core.pipeline_controller import ScientificPipelineController
from backend.workers.queue_executor import start_background_worker_queue
from backend.workers.task_manager import TaskManager

async def run_regression_test():
    # 1. Start worker threads
    start_background_worker_queue()
    
    # 2. Setup mock data
    csv_path = "tests_mock_data.csv"
    with open(csv_path, "w") as f:
        f.write("smiles,endpoint_val,endpoint_cat\nCCO,1.2,Active\nCCN,0.8,Inactive\n")
        
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    workspace_id = "test_workspace_999"
    context = registry.get_context(workspace_id)
    
    print("\n--- PHASE 1: Ingest ---")
    res = await ScientificPipelineController.ingest_dataset(context, csv_path, csv_path, file_bytes)
    assert res["success"] is True
    assert res["row_count"] == 2
    
    print("\n--- PHASE 2: Mapping ---")
    mappings = {"endpoint_cat": "endpoint", "endpoint_val": "value", "smiles": "smiles"}
    res = await ScientificPipelineController.apply_column_mapping(context, mappings)
    assert res["success"] is True
    
    print("\n--- PHASE 3: Segregation ---")
    res = await ScientificPipelineController.perform_segmentation(context)
    assert res["success"] is True
    assert "value_stats" in res["statistics"]
    assert res["statistics"]["value_stats"]["mean"] == 1.0  # (1.2 + 0.8) / 2
    
    print("\n--- PHASE 4: Enrichment ---")
    job_id = await ScientificPipelineController.run_enrichment(context, selected_descriptors=[], include_mordred=False, mode="fast")
    assert job_id is not None
    
    print(f"Job Dispatched: {job_id}. Waiting for completion...")
    while True:
        status = TaskManager.query_status(job_id)
        if status["status"] == "COMPLETED":
            break
        elif status["status"] in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Job failed: {status}")
        await asyncio.sleep(0.5)
        
    print("\n--- PHASE 5: Assembly ---")
    res = await ScientificPipelineController.assemble_enrichment_result(context)
    assert res["total_rows"] == 2
    assert len(res["columns"]) > 10
    
    print("\n--- PHASE 6: Readiness ---")
    res = await ScientificPipelineController.run_readiness_analysis(context)
    print("Readiness Tier:", res["tier"], "Score:", res["score"])
    
    # Assert Strict Numerical Parity
    assert res["tier"] == "Tier C (Not Modeling Fit)", f"Unexpected Tier: {res['tier']}"
    assert res["score"] == 53.7, f"Unexpected Score: {res['score']}"
    assert isinstance(res["deductions"], list)
    
    print("\n[SUCCESS] SCIENTIFIC PARITY REGRESSION TEST PASSED.")
    print(f"Execution Trace: {context.execution_trace}")
    print(f"Snapshots Saved: {len(context.snapshots)}")
    
    os.remove(csv_path)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    asyncio.run(run_regression_test())

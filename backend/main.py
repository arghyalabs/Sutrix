import os
import json
import logging
import asyncio
import zipfile
import io
from typing import Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import multiprocessing

# Windows Multiprocessing Fix (Improvement 8)
if __name__ == '__main__':
    multiprocessing.freeze_support()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("sdo.backend.gateway")

from backend.core.workspace_registry import registry, registry_cleanup_loop
from backend.core.pipeline_controller import ScientificPipelineController
from backend.workers.queue_executor import start_background_worker_queue, job_registry
from backend.workers.websocket_manager import ws_broadcaster
from backend.workers.task_manager import TaskManager
from backend.optimization.memory_guard import MemoryGuard
from backend.api.validators.request_validator import (
    BaseClientPayload, CurationPayload, MappingPayload,
    SchemaInferPayload, SegregatePayload, EnrichmentPayload,
    validate_uploaded_file
)
from backend.api.routes.hierarchy_routes import router as hierarchy_router
from backend.api.routes.descriptor_routes import router as descriptor_router
from backend.api.routes.modeling_routes import router as modeling_router
from backend.core.config import settings

app = FastAPI(title="Scientific Data Orchestrator", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular API routers
app.include_router(hierarchy_router)
app.include_router(descriptor_router)
app.include_router(modeling_router)

memory_guard = MemoryGuard()

@app.on_event("startup")
async def startup_event():
    logger.info("SDO SaaS Engine launching...")
    # Initialize Sentry from env variables
    from backend.logging.logger import initialize_sentry
    initialize_sentry()
    
    start_background_worker_queue()
    asyncio.create_task(registry_cleanup_loop())
    asyncio.create_task(ws_broadcaster.start_heartbeat_monitor())

# ── 1. FILE INGESTION ────────────────────────────────────────
@app.post("/api/ingest")
async def api_ingest(file: UploadFile = File(...), client_id: str = Form(...)):
    is_safe, msg = memory_guard.verify_safety_shield()
    if "EMERGENCY" in msg:
        raise HTTPException(status_code=503, detail=msg)
        
    try:
        file_bytes = await file.read()
        validate_uploaded_file(file.filename, len(file_bytes), file.content_type)
        active_uploads = os.path.join(settings.UPLOAD_DIR, "active")
        os.makedirs(active_uploads, exist_ok=True)
        temp_path = os.path.join(active_uploads, file.filename)
        with open(temp_path, "wb") as f:
            f.write(file_bytes)
            
        context = registry.get_context(client_id)
        result = await ScientificPipelineController.ingest_dataset(context, file.filename, temp_path, file_bytes)
        return result
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/demo_ingest")
async def api_demo_ingest(client_id: str = Form(...)):
    is_safe, msg = memory_guard.verify_safety_shield()
    if "EMERGENCY" in msg:
        raise HTTPException(status_code=503, detail=msg)
        
    try:
        # Resolve path to demo dataset in the project root
        demo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eco_toxicity_dataset.csv")
        if not os.path.exists(demo_path):
            raise FileNotFoundError("eco_toxicity_dataset.csv not found in project root.")
            
        with open(demo_path, "rb") as f:
            file_bytes = f.read()
            
        context = registry.get_context(client_id)
        result = await ScientificPipelineController.ingest_dataset(context, "eco_toxicity_dataset.csv", demo_path, file_bytes)
        return result
    except Exception as e:
        logger.error(f"Demo Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 2. MAPPING & CURATION ────────────────────────────────────────
@app.post("/api/curate")
async def api_curate(payload: CurationPayload):
    try:
        context = registry.get_context(payload.client_id)
        return await ScientificPipelineController.curate_columns(context, payload.columns_to_drop)
    except Exception as e:
        logger.error(f"Curation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mapping")
async def api_mapping(payload: MappingPayload):
    try:
        context = registry.get_context(payload.client_id)
        return await ScientificPipelineController.apply_column_mapping(context, payload.mappings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from backend.core.schema_intelligence import SchemaIntelligenceEngine

@app.post("/api/schema/infer")
async def api_schema_infer(payload: SchemaInferPayload):
    try:
        inferred = SchemaIntelligenceEngine.infer_schema(payload.columns)
        return {"mappings": inferred}
    except Exception as e:
        logger.error(f"Schema Inference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 3. SEGREGATION ────────────────────────────────────────
@app.post("/api/segregate")
async def api_segregate(payload: SegregatePayload):
    try:
        context = registry.get_context(payload.client_id)
        job_id = await ScientificPipelineController.perform_segmentation(
            context=context,
            enable_dedup=payload.enable_dedup,
            enable_variance_pruning=payload.enable_variance_pruning,
            prune_high_variance=payload.prune_high_variance,
            selected_hierarchy=payload.selected_hierarchy
        )
        return {"job_id": job_id, "status": "QUEUED"}
    except Exception as e:
        logger.error(f"Segregation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 4. ENRICHMENT ────────────────────────────────────────
@app.post("/api/jobs/enrich")
async def api_enrich_submit(payload: EnrichmentPayload):
    try:
        context = registry.get_context(payload.client_id)
        job_id = await ScientificPipelineController.run_enrichment(
            context, payload.selected_descriptors, payload.include_mordred, payload.mode
        )
        return {"job_id": job_id, "status": "QUEUED"}
    except Exception as e:
        logger.error(f"Enrichment job failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{client_id}/status")
async def api_job_status(client_id: str):
    context = registry.get_context(client_id)
    if not context.active_job_id:
        raise HTTPException(status_code=404, detail="No active job")
    status = TaskManager.query_status(context.active_job_id)
    return status

@app.post("/api/jobs/{client_id}/cancel")
async def api_job_cancel(client_id: str):
    context = registry.get_context(client_id)
    if not context.active_job_id:
        raise HTTPException(status_code=404, detail="No active job")
    success = TaskManager.cancel_job(context.active_job_id)
    return {"success": success}

@app.get("/api/jobs/{client_id}/result")
async def api_job_result(client_id: str):
    try:
        context = registry.get_context(client_id)
        return await ScientificPipelineController.assemble_enrichment_result(context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── 5. READINESS ────────────────────────────────────────
@app.post("/api/readiness")
async def api_readiness(payload: BaseClientPayload):
    try:
        context = registry.get_context(payload.client_id)
        return await ScientificPipelineController.run_readiness_analysis(context)
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 6. TELEMETRY ─────────────────────────────────────
@app.get("/api/telemetry")
async def api_telemetry():
    status = memory_guard.get_memory_status()
    from backend.cache.descriptor_cache import ScientificDescriptorCache
    cache = ScientificDescriptorCache()
    cache_stats = cache.get_statistics()
    status["cache_hit_rate_pct"] = cache_stats["hit_rate_pct"]
    status["total_cached_compounds"] = cache_stats["total_cached_compounds"]
    status["active_jobs_count"] = len(job_registry.get_active_jobs())
    status["active_workspaces"] = len(registry.workspaces)
    return status

# ── 6b. COMPLIANCE & SEGREGATION DOWNLOADS ─────────────────
@app.get("/api/segregate/{client_id}/download")
async def api_segregate_download(client_id: str):
    try:
        context = registry.get_context(client_id)
        result = context.active_segregation_result
        if not result:
            raise HTTPException(status_code=404, detail="No segregation result found in session context.")
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for leaf in result.leaf_nodes:
                rel_path = leaf['path']
                filename = leaf['filename']
                file_buffer = leaf.get('buffer')
                if file_buffer:
                    zip_entry_path = f"{result.root_path}/{rel_path}/{filename}" if rel_path else f"{result.root_path}/{filename}"
                    zipf.writestr(zip_entry_path, file_buffer.getvalue())
                    
        zip_buffer.seek(0)
        filename = f"SDO_Raw_Segregation_{client_id}.zip"
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Segregation download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/{client_id}/report")
async def api_compliance_report(client_id: str):
    try:
        context = registry.get_context(client_id)
        df = context.load_slice()
        
        # 1. Run audit
        from backend.processing.auditor import ScientificAuditor
        auditor = ScientificAuditor()
        report = auditor.audit(df, context.mappings, dataset_id=client_id)
        
        # 2. Recover stats
        seg_stats = context.segmentation_results or {}
        variance_summary = None
        if context.active_segregation_result:
            variance_summary = context.active_segregation_result.variance_summary
            
        dedup_stats_dict = None
        if "dedup_stats" in seg_stats and seg_stats["dedup_stats"]:
            d = seg_stats["dedup_stats"]
            dedup_stats_dict = {
                "original_count": d["original_count"],
                "deduplicated_count": d["deduplicated_count"],
                "duplicates_removed": d["duplicates_removed"],
                "duplicate_groups": d["duplicate_groups"],
            }
            
        from backend.exports.pdf_generator import AuditPDFGenerator
        pdf_gen = AuditPDFGenerator()
        pdf_io = pdf_gen.generate_report(
            audit_report=report,
            dataset_name=f"dataset_{client_id}",
            session_id=client_id,
            variance_report=variance_summary,
            dedup_stats=dedup_stats_dict,
        )
        
        filename = f"Scientific_Audit_Report_{client_id}.pdf"
        return StreamingResponse(
            pdf_io,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Compliance report download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/compliance/{client_id}/download")
async def api_compliance_download(client_id: str):
    try:
        context = registry.get_context(client_id)
        result = context.active_segregation_result
        if not result:
            raise HTTPException(status_code=404, detail="No segregation result found in session context. Map columns and run segregation first.")
            
        df = context.load_slice()
        
        # 1. Run audit
        from backend.processing.auditor import ScientificAuditor
        auditor = ScientificAuditor()
        report = auditor.audit(df, context.mappings, dataset_id=client_id)
        
        # 2. Recover stats
        seg_stats = context.segmentation_results or {}
        variance_summary = result.variance_summary
            
        dedup_stats_dict = None
        if "dedup_stats" in seg_stats and seg_stats["dedup_stats"]:
            d = seg_stats["dedup_stats"]
            dedup_stats_dict = {
                "original_count": d["original_count"],
                "deduplicated_count": d["deduplicated_count"],
                "duplicates_removed": d["duplicates_removed"],
                "duplicate_groups": d["duplicate_groups"],
            }
        
        # 3. Generate hyperlinked excel index, manifest, and PDF report
        from backend.exports.index_generator import MasterIndexGenerator
        index_gen = MasterIndexGenerator()
        
        manifest_json = index_gen.generate_from_segregation_result(
            result=result,
            session_id=client_id,
            file_hash="snappy_parquet_hash",
            audit_score=report.quality_score,
            dataset_name=f"dataset_{client_id}",
            dedup_stats=dedup_stats_dict,
            variance_summary=variance_summary,
        )
        
        consistency_score = variance_summary.consistency_score if variance_summary else None
        master_index_io = index_gen.generate_excel_index(result, consistency_score=consistency_score)
        
        from backend.exports.pdf_generator import AuditPDFGenerator
        pdf_gen = AuditPDFGenerator()
        pdf_io = pdf_gen.generate_report(
            audit_report=report,
            dataset_name=f"dataset_{client_id}",
            session_id=client_id,
            variance_report=variance_summary,
            dedup_stats=dedup_stats_dict,
        )
        
        # 4. Assemble compliance memory ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Root metadata artifacts
            zipf.writestr(f"{result.root_path}/manifest.json", manifest_json)
            zipf.writestr(f"{result.root_path}/Master_Index.xlsx", master_index_io.getvalue())
            zipf.writestr(f"{result.root_path}/Scientific_Audit_Report.pdf", pdf_io.getvalue())
            
            # Segregated excel files
            for leaf in result.leaf_nodes:
                rel_path = leaf['path']
                filename = leaf['filename']
                file_buffer = leaf.get('buffer')
                if file_buffer:
                    zip_entry_path = f"{result.root_path}/{rel_path}/{filename}" if rel_path else f"{result.root_path}/{filename}"
                    zipf.writestr(zip_entry_path, file_buffer.getvalue())
                    
        zip_buffer.seek(0)
        filename = f"SDO_Compliance_{client_id}.zip"
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Compliance package download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── 7. WEBSOCKET ──────────────────────────────────────
@app.websocket("/ws/jobs/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Observation ONLY. No mutations permitted."""
    await ws_broadcaster.connect(client_id, websocket)
    
    # Send immediate state recovery frame to prevent WebSocket race conditions (stale/fast jobs)
    try:
        context = registry.get_context(client_id)
        if context and context.active_job_id:
            job = job_registry.get_job(context.active_job_id)
            if job:
                status = job.get("status")
                if status == "COMPLETED":
                    await websocket.send_text(json.dumps({
                        "job_id": context.active_job_id,
                        "type": "JOB_COMPLETED",
                        "data": {
                            "progress_pct": 100,
                            "eta_seconds": 0.0,
                            "compounds_per_sec": job.get("compounds_per_sec", 0.0),
                            "phase": "Complete",
                            "logs": ["🏁 Scientific workflow complete! Releasing RAM locks."]
                        }
                    }))
                elif status == "FAILED":
                    await websocket.send_text(json.dumps({
                        "job_id": context.active_job_id,
                        "type": "JOB_FAILED",
                        "error": job.get("error_message") or "Unknown error"
                    }))
                elif status == "CANCELLED":
                    await websocket.send_text(json.dumps({
                        "job_id": context.active_job_id,
                        "type": "JOB_CANCELLED"
                    }))
                elif status in ["RUNNING", "QUEUED"]:
                    await websocket.send_text(json.dumps({
                        "job_id": context.active_job_id,
                        "type": "PROGRESS",
                        "data": {
                            "progress_pct": job.get("progress", 0),
                            "eta_seconds": job.get("eta_seconds", 0.0),
                            "compounds_per_sec": job.get("compounds_per_sec", 0.0),
                            "phase": "🔍 Running" if status == "RUNNING" else "⏳ Queued",
                            "logs": ["Active task context re-established."]
                        }
                    }))
    except Exception as e:
        logger.error(f"Failed to send state recovery frame: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            # Ignore all payloads to prevent state mutation
            msg = json.loads(data)
            if msg.get("type") == "PONG":
                pass
    except WebSocketDisconnect:
        ws_broadcaster.disconnect(client_id)
    except Exception as e:
        ws_broadcaster.disconnect(client_id)

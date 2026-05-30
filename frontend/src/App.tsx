import React, { useState, useRef, useCallback, useEffect, lazy, Suspense } from 'react';
import { Toaster, toast } from 'react-hot-toast';

// API Services Resilience Layer
import { uploadApi } from './services/uploadApi';
import { mappingApi } from './services/mappingApi';
import { enrichmentApi } from './services/enrichmentApi';
import { readinessApi } from './services/readinessApi';
import { workspaceApi } from './services/workspaceApi';

// Store & Sockets
import { useWorkspaceStore } from './store/useWorkspaceStore';
import { useWebSocket } from './performance/useWebSocket';

// Components
import { LandingPage } from './components/landing/LandingPage';
import { DashboardLayout } from './components/dashboard/DashboardLayout';
import { UploadWorkspace } from './components/upload/UploadWorkspace';
import { DatasetMapping } from './components/mapping/DatasetMapping';
import { HierarchyBuilder } from './components/segregation/HierarchyBuilder';
import { DataAnalysisWorkspace } from './components/analysis/DataAnalysisWorkspace';
import { DescriptorEnrichment } from './components/enrichment/DescriptorEnrichment';
import { ReadinessDashboard } from './components/readiness/ReadinessDashboard';
import ModelingReadinessWorkspace from './components/modeling/ModelingReadinessWorkspace';
import { modelingApi } from './services/modelingApi';
import { ReportsExport } from './components/reports/ReportsExport';
import { BenchmarkPanel } from './components/telemetry/BenchmarkPanel';
import { CompoundExplorer } from './components/reports/CompoundExplorer';

// AGPL-3.0 Compliance Views
import { LicenseGate } from './components/license/LicenseGate';
import { LicenseModal } from './components/license/LicenseModal';
import { SUTRIXLogo, LogoLoader } from './components/ui/SUTRIXLogo';
import { LoadingScreen } from './components/ui/LoadingScreen';

// ===========================================================================
// ERROR BOUNDARY – catches React render crashes and shows a recoverable UI
// instead of a full black screen
// ===========================================================================
class ErrorBoundary extends React.Component<
  { children: React.ReactNode; onReset: () => void },
  { hasError: boolean; errorMessage: string }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, errorMessage: error?.message || 'Unknown error' };
  }

  componentDidCatch(error: Error, info: any) {
    console.error('[ErrorBoundary] Caught:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full min-h-[60vh] text-center px-8">
          <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-6">
            <span className="text-rose-400 text-2xl font-bold">!</span>
          </div>
          <h2 className="text-white font-bold text-lg mb-2">Something went wrong</h2>
          <p className="text-white/40 text-sm mb-2 max-w-md">{this.state.errorMessage}</p>
          <p className="text-white/30 text-xs mb-6 max-w-md">
            Your workspace data is still saved. Use the sidebar to navigate back to a previous step.
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, errorMessage: '' });
              this.props.onReset();
            }}
            className="px-6 py-2.5 rounded-xl bg-cyan-500/20 text-cyan-400 font-bold hover:bg-cyan-500/30 transition-colors"
          >
            Go Back to Enrichment
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const App: React.FC = () => {
  const storeWorkspaceId = useWorkspaceStore(s => s.workspaceId);
  const generatedClientId = useRef(`SDO_CORE_${Math.random().toString(36).substring(2, 9)}`).current;
  const clientId = storeWorkspaceId || generatedClientId;
  
  const [hasLaunched, setHasLaunched] = useState(false);
  const [isAppLoading, setIsAppLoading] = useState(false);

  // AGPL-3.0 Open-Source License compliance state variables
  const [licenseAccepted, setLicenseAccepted] = useState(() => {
    return localStorage.getItem('sdo_agpl_agreed') === 'true';
  });
  const [isLicenseModalOpen, setIsLicenseModalOpen] = useState(false);

  const handleAcceptLicense = () => {
    localStorage.setItem('sdo_agpl_agreed', 'true');
    setLicenseAccepted(true);
  };

  const {
    activeTab, setActiveTab,
    filename, parquetPath, rowCount, columns, preview, setDataset,
    mappings, setMappings,
    enrichmentMode, setEnrichmentMode,
    includeMordred, setIncludeMordred,
    readiness, setReadiness, readinessLoading, setReadinessLoading,
    activeJobId, setActiveJobId, setActiveJobType,
    modelingAnalysis, setModelingAnalysis, modelingLoading, setModelingLoading,
    modelingActivePanel, setModelingActivePanel,
    resetWorkspace
  } = useWorkspaceStore();

  const socket = useWebSocket(clientId);

  // ── Upload processing state ──────────────────────────────────
  const [isUploadProcessing, setIsUploadProcessing] = useState(false);
  const [uploadJobId, setUploadJobId] = useState<string | null>(null);
  // Ref for synchronous access in WS listener (avoids stale-closure race)
  const uploadJobIdRef = useRef<string | null>(null);
  const [uploadStage, setUploadStage] = useState('');
  const [uploadMessage, setUploadMessage] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadEta, setUploadEta] = useState(0);
  const [uploadItemsPerSec, setUploadItemsPerSec] = useState(0);
  const [uploadLogs, setUploadLogs] = useState<string[]>([]);

  // Listen to WebSocket for upload job completion
  useEffect(() => {
    const wsState = socket as any;
    const rawMsg = wsState?.lastMessage;
    if (!rawMsg) return;
    // Use ref for synchronous job_id check (avoids race with setState)
    if (!uploadJobIdRef.current) return;
    try {
      const msg = typeof rawMsg === 'string' ? JSON.parse(rawMsg) : rawMsg;
      // Accept messages by job_id OR by workspace_id (broadcast)
      const jobIdMatch = uploadJobIdRef.current && msg.job_id === uploadJobIdRef.current;
      const wsIdMatch = msg.workspace_id === clientId;
      if (!jobIdMatch && !wsIdMatch) return;

      if (msg.type === 'STAGE_CHANGE') {
        setUploadStage(msg.stage || '');
        setUploadMessage(msg.description || '');
      }
      if (msg.type === 'PROGRESS_UPDATE') {
        setUploadProgress(msg.progress || 0);
        setUploadEta(msg.eta_seconds || 0);
        setUploadItemsPerSec(msg.items_per_sec || 0);
        setUploadStage(msg.stage || uploadStage);
        setUploadMessage(msg.message || '');
        if (msg.logs?.length) setUploadLogs(msg.logs);
      }
      if (msg.type === 'JOB_COMPLETED') {
        const d = msg.result || {};
        if (d.filename || d.row_count) {
          setDataset(d.filename, d.parquet_path, d.row_count, d.columns, d.preview);
          // Auto-infer schema
          if (d.columns?.length) {
            mappingApi.inferSchema(d.columns).then(schemaRes => {
              const aiMappings: any = {};
              const inferenceDetails: any = {};
              schemaRes.mappings.forEach((m: any) => {
                aiMappings[m.column] = m.mapped_to;
                inferenceDetails[m.column] = { confidence: m.confidence, reasons: m.reasons };
              });
              setMappings(aiMappings);
              const store = useWorkspaceStore.getState();
              if (store.setMappingIntelligence) store.setMappingIntelligence(inferenceDetails);
            }).catch(() => {
              const fallback: any = {};
              d.columns.forEach((c: string) => { fallback[c] = 'none'; });
              setMappings(fallback);
            });
          }
        }
        setIsUploadProcessing(false);
        setUploadProgress(100);
        toast.success('Dataset ingested and workspace ready!');
      }
      if (msg.type === 'JOB_FAILED') {
        setIsUploadProcessing(false);
        toast.error(`Ingestion failed: ${msg.error}`);
      }
      if (msg.type === 'PARTIAL_SAVE') {
        setIsUploadProcessing(false);
        toast('Processing cancelled. Progress saved.', { icon: '⚠️' });
      }
    } catch {
      // ignore parse errors
    }
  }, [(socket as any)?.lastMessage, uploadJobId]);

  const handleLaunch = () => {
    setHasLaunched(true);
    useWorkspaceStore.getState().setWorkspaceId(clientId);
    window.location.hash = useWorkspaceStore.getState().activeTab;
  };

  React.useEffect(() => {
    const handlePopState = () => {
    const hash = window.location.hash.replace('#', '');
      const validTabs = ['ingest', 'mapping', 'hierarchy', 'analysis', 'enrichment', 'readiness', 'verification', 'reports'];
      if (validTabs.includes(hash)) {
        setActiveTab(hash);
      }
    };
    
    if (hasLaunched && !window.location.hash) {
      window.location.hash = activeTab;
    }

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [hasLaunched, activeTab, setActiveTab]);

  const handleExit = () => {
    setHasLaunched(false);
    socket.resetSocketState();
    resetWorkspace();
    // Explicitly clear stale job state so re-entry doesn't fire assembly calls
    useWorkspaceStore.getState().setActiveJobId('');
    useWorkspaceStore.getState().setActiveJobType(null);
  };

  const handleIngestFile = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];
    try {
      setIsUploadProcessing(true);
      setUploadProgress(0);
      setUploadStage('UPLOADING');
      setUploadMessage(`Uploading ${file.name}...`);
      setUploadLogs([]);
      const res = await uploadApi.ingestFile(file, clientId);
      // res now returns { job_id, status: 'PROCESSING', filename, eta_seconds }
      if (res.job_id) {
        uploadJobIdRef.current = res.job_id;  // sync ref for WS race-safety
        setUploadJobId(res.job_id);
        setUploadEta(res.eta_seconds || 0);
        setUploadStage('PARSING');
        setUploadMessage('Parsing dataset...');
        // Primary: WebSocket JOB_COMPLETED. Fallback: poll /api/jobs/{id} in case WS missed event.
        const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
        const jobId = res.job_id;
        const poll = async () => {
          for (let i = 0; i < 15; i++) {
            if (useWorkspaceStore.getState().rowCount > 0) return; // WS delivered
            try {
              const r2 = await fetch(`${apiBase}/api/jobs/${jobId}`);
              if (!r2.ok) {
                await new Promise(r => setTimeout(r, 2000));
                continue;
              }
              const job = await r2.json();
              if (job.status === 'COMPLETED' && job.result?.row_count > 0) {
                const d = job.result;
                setDataset(d.filename || file.name, d.parquet_path, d.row_count, d.columns, d.preview ?? []);
                
                // Auto-infer schema on fallback
                if (d.columns?.length) {
                  mappingApi.inferSchema(d.columns).then(schemaRes => {
                    const aiMappings: any = {};
                    const inferenceDetails: any = {};
                    schemaRes.mappings.forEach((m: any) => {
                      aiMappings[m.column] = m.mapped_to;
                      inferenceDetails[m.column] = { confidence: m.confidence, reasons: m.reasons };
                    });
                    setMappings(aiMappings);
                    const store = useWorkspaceStore.getState();
                    if (store.setMappingIntelligence) store.setMappingIntelligence(inferenceDetails);
                  }).catch(() => {
                    const fallback: any = {};
                    d.columns.forEach((c: string) => { fallback[c] = 'none'; });
                    setMappings(fallback);
                  });
                }
                setIsUploadProcessing(false);
                setUploadProgress(100);
                toast.success('Dataset ingested and workspace ready!');
                return;
              }
              if (job.status === 'FAILED') {
                setIsUploadProcessing(false);
                toast.error(`Ingestion failed: ${job.error}`);
                return;
              }
            } catch { /* WS will deliver */ }
            await new Promise(r => setTimeout(r, 1000));
          }
        };
        poll();
      } else {
        // Fallback: legacy sync response (backend always returns job_id now)
        const legacy = res as any;
        setDataset(res.filename, legacy.parquet_path ?? '', legacy.row_count ?? 0, legacy.columns ?? [], legacy.preview ?? []);
        setIsUploadProcessing(false);
        toast.success('Dataset ingested.');
      }
    } catch (error: any) {
      setIsUploadProcessing(false);
      toast.error(error.response?.data?.detail || 'Upload failed');
    }
  }, [clientId]);


  const handleLoadDemo = useCallback(async () => {
    try {
      setIsUploadProcessing(true);
      setUploadProgress(0);
      setUploadStage('PARSING');
      setUploadMessage('Loading eco-toxicity demo dataset...');
      setUploadLogs([]);
      const res = await workspaceApi.loadDemoDataset(clientId);
      if (res.job_id) {
        uploadJobIdRef.current = res.job_id;
        setUploadJobId(res.job_id);
        setUploadEta(res.eta_seconds || 0);
        // Primary: WebSocket JOB_COMPLETED. Fallback: poll /api/jobs/{id} in case WS missed event.
        const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
        const jobId = res.job_id;
        const poll = async () => {
          for (let i = 0; i < 15; i++) {
            if (useWorkspaceStore.getState().rowCount > 0) return; // WS delivered
            try {
              const r2 = await fetch(`${apiBase}/api/jobs/${jobId}`);
              if (!r2.ok) {
                await new Promise(r => setTimeout(r, 2000));
                continue;
              }
              const job = await r2.json();
              if (job.status === 'COMPLETED' && job.result?.row_count > 0) {
                const d = job.result;
                setDataset(d.filename || res.filename, d.parquet_path, d.row_count, d.columns, d.preview ?? []);
                
                // Auto-infer schema on fallback
                if (d.columns?.length) {
                  mappingApi.inferSchema(d.columns).then(schemaRes => {
                    const aiMappings: any = {};
                    const inferenceDetails: any = {};
                    schemaRes.mappings.forEach((m: any) => {
                      aiMappings[m.column] = m.mapped_to;
                      inferenceDetails[m.column] = { confidence: m.confidence, reasons: m.reasons };
                    });
                    setMappings(aiMappings);
                    const store = useWorkspaceStore.getState();
                    if (store.setMappingIntelligence) store.setMappingIntelligence(inferenceDetails);
                  }).catch(() => {
                    const fallback: any = {};
                    d.columns.forEach((c: string) => { fallback[c] = 'none'; });
                    setMappings(fallback);
                  });
                }
                setIsUploadProcessing(false);
                setUploadProgress(100);
                  toast.success('Dataset ingested and workspace ready!');
                  return;
                }
                if (job.status === 'FAILED') {
                  setIsUploadProcessing(false);
                  toast.error(`Demo load failed: ${job.error}`);
                  return;
                }
            } catch { /* WS will deliver */ }
            await new Promise(r => setTimeout(r, 1000));
          }
        };
        poll();
      } else {
        const legacy = res as any;
        setDataset(res.filename, legacy.parquet_path ?? '', legacy.row_count ?? 0, legacy.columns ?? [], legacy.preview ?? []);
        setIsUploadProcessing(false);
        toast.success('Demo dataset loaded.');
      }
    } catch (error: any) {
      setIsUploadProcessing(false);
      toast.error(error.response?.data?.detail || 'Failed to load demo dataset');
    }
  }, [clientId]);


  const handleCurateColumns = async (colsToDrop: string[]) => {
    try {
      const toastId = toast.loading('Sanitizing and dropping unneeded columns...');
      const d = await uploadApi.curateColumns(colsToDrop, clientId);
      toast.success('Dataset curated successfully.', { id: toastId });
      setDataset(filename || 'dataset.parquet', d.parquet_path, d.row_count, d.columns, d.preview);
      setActiveTab('mapping');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Curation failed');
    }
  };

  const handleSaveMappings = async () => {
    try {
      const toastId = toast.loading('Saving mappings and running segregation...');
      
      // 1. Establish bindings
      const mapRes = await mappingApi.saveMappings(mappings, clientId);
      
      if (mapRes.mappings) {
        setMappings(mapRes.mappings as any);
        if (mapRes.columns) {
          setDataset(filename || 'dataset.parquet', parquetPath, rowCount, mapRes.columns, preview);
        }
      }
      
      if (mapRes.dataset_type) {
        toast.success(`Dataset classified: ${mapRes.dataset_type}`, {
          icon: '🧠',
          duration: 5000
        });
      }
      
      if (mapRes.warnings && mapRes.warnings.length > 0) {
        mapRes.warnings.forEach((warn: string) => {
          toast.error(warn, {
            icon: '⚠️',
            duration: 8000
          });
        });
      }
      
      toast.success('Mapping complete. Proceed to Hierarchy Builder.', { id: toastId });
      
      setActiveTab('hierarchy');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Mapping failed');
    }
  };

  const handleRunEnrichment = async () => {
    try {
      const storeState = useWorkspaceStore.getState();
      const response = await enrichmentApi.runEnrichment(
        storeState.selectedDescriptors,
        storeState.includeMordred,
        storeState.enrichmentMode,
        clientId
      );
      
      setActiveJobId(response.job_id);
      setActiveJobType('enrichment');
      socket.connectToJob(response.job_id);
      toast.success('Parallel calculation job dispatched.');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to start job');
    }
  };

  const handleCancelJob = useCallback(async (jobId?: string) => {
    try {
      const targetId = jobId || useWorkspaceStore.getState().activeJobId;
      if (!targetId) return;
      // Cancel upload job
      if (targetId === uploadJobId) {
        await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/api/jobs/${targetId}/cancel`, { method: 'POST' });
        setIsUploadProcessing(false);
        toast('Upload cancelled. Partial progress saved.', { icon: '⚠️' });
        return;
      }
      await enrichmentApi.cancelJob(clientId);
      toast.error('Job cancellation requested.');
    } catch {
      toast.error('Failed to cancel job');
    }
  }, [clientId, uploadJobId]);


  const handleFetchEnrichmentResults = async () => {
    try {
      const storeState = useWorkspaceStore.getState();
      if (!storeState.activeJobId) {
        toast.error('No enrichment job found. Please run enrichment first.');
        return;
      }
      if (storeState.activeJobType !== 'enrichment') {
        toast.error('The last job was not an enrichment job. Please run enrichment first.');
        return;
      }
      
      const toastId = toast.loading('Assembling enriched parquet...');
      const d = await enrichmentApi.fetchResults(clientId, storeState.activeJobId);
      toast.success('Enrichment matrix loaded.', { id: toastId });
      
      setDataset(d.job_id + '.parquet', d.parquet_path, d.total_rows, d.columns, d.preview);
      

      setActiveTab('readiness');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to fetch results');
    }
  };

  const handleRecalculateAudit = async () => {
    const t = toast.loading('Recalculating audit...');
    try {
      const auditRes = await readinessApi.evaluateReadiness(clientId);
      setReadiness(auditRes as any);
      toast.success('Audit recalculated', { id: t });
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Failed to recalculate', { id: t });
    }
  };

  if (!hasLaunched && !isAppLoading) {
    return <LandingPage onLaunch={handleLaunch} />;
  }

  // Calculate generic telemetry data to pass to topbar
  const mockTelemetry = {
    ram_usage_pct: Math.floor(40 + Math.random() * 20),
    fps: 60,
    active_jobs_count: socket.jobStatus === 'RUNNING' ? 1 : 0
  };

  const renderContent = () => {
    switch (activeTab) {
      case 'ingest':
        return (
          <UploadWorkspace
            filename={filename} rowCount={rowCount} columns={columns} preview={preview}
            isProcessing={isUploadProcessing}
            processingStage={uploadStage}
            processingMessage={uploadMessage}
            processingProgress={uploadProgress}
            processingEta={uploadEta}
            processingItemsPerSec={uploadItemsPerSec}
            processingStageLogs={uploadLogs}
            activeJobId={uploadJobId}
            handleIngestFile={handleIngestFile}
            handleLoadDemo={handleLoadDemo}
            handleCurateColumns={handleCurateColumns}
            onCancelJob={handleCancelJob}
          />
        );
      case 'mapping':
        return (
          <DatasetMapping
            columns={columns} mappings={mappings} setMappings={setMappings}
            handleSaveMappings={handleSaveMappings}
          />
        );
      case 'hierarchy':
        return <HierarchyBuilder clientId={clientId} socket={socket} />;
      case 'analysis':
        return <DataAnalysisWorkspace />;
      case 'enrichment':
        return (
          <DescriptorEnrichment
            enrichmentMode={enrichmentMode} setEnrichmentMode={setEnrichmentMode}
            includeMordred={includeMordred} setIncludeMordred={setIncludeMordred}
            handleRunEnrichment={handleRunEnrichment} handleCancelJob={handleCancelJob}
            handleFetchEnrichmentResults={handleFetchEnrichmentResults}
            socket={socket} ramUsage={mockTelemetry.ram_usage_pct} fps={60}
          />
        );
      case 'readiness':
        return (
          <ModelingReadinessWorkspace
            clientId={clientId}
            modelingAnalysis={modelingAnalysis}
            modelingLoading={modelingLoading}
            onRunAnalysis={async () => {
              setModelingLoading(true);
              try {
                const result = await modelingApi.runAnalysis(clientId);
                setModelingAnalysis(result);
                toast.success('AI Analysis complete!');
              } catch (e: any) {
                toast.error(e.response?.data?.detail || 'Analysis failed');
              } finally {
                setModelingLoading(false);
              }
            }}
            activePanel={modelingActivePanel}
            setActivePanel={setModelingActivePanel}
          />
        );
      case 'verification':
        return (
          <CompoundExplorer
            clientId={clientId}
            activeJobId={activeJobId || null}
          />
        );
      case 'benchmark':
        return <BenchmarkPanel />;
      case 'reports':
        return (
          <ReportsExport
            clientId={clientId}
            activeJobId={activeJobId || null}
            handleResetWorkspace={handleExit}
          />
        );
      default:
        return <UploadWorkspace filename={filename} rowCount={rowCount} columns={columns} preview={preview} handleIngestFile={handleIngestFile} handleLoadDemo={handleLoadDemo} handleCurateColumns={handleCurateColumns} />;
    }
  };

  if (!licenseAccepted) {
    return <LicenseGate onAccept={handleAcceptLicense} />;
  }

  return (
    <>
      <LoadingScreen isLoading={isAppLoading} />
      <Toaster position="top-right" toastOptions={{ 
        className: '!bg-[#111827] !text-white !border !border-white/[0.08] !shadow-2xl',
        loading: {
          icon: <LogoLoader size="w-5 h-5" compact />,
        }
      }} />
      <DashboardLayout
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onExit={handleExit}
        onGoHome={() => setHasLaunched(false)}
        onOpenLicense={() => setIsLicenseModalOpen(true)}
        telemetryData={mockTelemetry}
      >
        <ErrorBoundary key={activeTab} onReset={() => setActiveTab('enrichment')}>
          {renderContent()}
        </ErrorBoundary>
      </DashboardLayout>
      <LicenseModal isOpen={isLicenseModalOpen} onClose={() => setIsLicenseModalOpen(false)} />
    </>
  );
};

export default App;

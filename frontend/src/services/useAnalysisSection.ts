/**
 * useAnalysisSection — shared hook for background-job analysis tabs.
 * Handles: triggering the job, listening for WS completion, fetching results.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { readinessApi } from './readinessApi';

type RunFn = (clientId: string) => Promise<{ job_id: string; section: string }>;

export function useAnalysisSection(
  clientId: string,
  section: string,
  runFn: RunFn
) {
  const [data, setData] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState('');
  const [error, setError] = useState<string | null>(null);
  const jobIdRef = useRef<string | null>(null);

  // Try to load cached result on mount
  useEffect(() => {
    if (!clientId) return;
    readinessApi.getSectionResult(clientId, section)
      .then((result: any) => setData(result))
      .catch(() => { /* not yet computed — that's fine */ });
  }, [clientId, section]);

  // WebSocket listener for job progress
  useEffect(() => {
    if (!clientId) return;

    const wsUrl = `ws://127.0.0.1:8000/ws/jobs/${clientId}`;
    let ws: WebSocket | null = null;

    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            if (
              (msg.type === 'ANALYSIS_PROGRESS' || msg.type === 'ANALYSIS_COMPLETE') &&
              msg.section === section &&
              (!jobIdRef.current || msg.job_id === jobIdRef.current)
            ) {
              setProgress(msg.progress_pct ?? 0);
              setPhase(msg.phase ?? '');
              if (msg.type === 'ANALYSIS_COMPLETE') {
                setIsRunning(false);
                // Fetch the results
                readinessApi.getSectionResult(clientId, section)
                  .then((result: any) => { setData(result); setError(null); })
                  .catch((e: any) => setError(String(e)));
              }
            }
            if (msg.type === 'ANALYSIS_ERROR' && msg.section === section) {
              setIsRunning(false);
              setError(msg.error || 'Analysis failed');
            }
          } catch (_) {}
        };
        ws.onerror = () => {};
      } catch (_) {}
    };

    connect();
    return () => { try { ws?.close(); } catch (_) {} };
  }, [clientId, section]);

  const run = useCallback(async () => {
    if (!clientId || isRunning) return;
    setIsRunning(true);
    setProgress(0);
    setPhase('Starting…');
    setError(null);
    try {
      const resp = await runFn(clientId);
      jobIdRef.current = resp.job_id;
    } catch (e: any) {
      setIsRunning(false);
      setError(e?.response?.data?.detail || String(e));
    }
  }, [clientId, isRunning, runFn]);

  return { data, isRunning, progress, phase, error, run };
}

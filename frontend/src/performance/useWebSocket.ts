import { useEffect, useState, useRef, useCallback } from 'react';
import toast from 'react-hot-toast';
import type { JobTelemetry, JobStatus } from '../types';
import { useWorkspaceStore } from '../store/useWorkspaceStore';

interface UseWebSocketReturn {
  isConnected: boolean;
  progress: number;
  eta: number;
  speed: number;
  phase: string;
  logs: string[];
  jobStatus: JobStatus | 'IDLE';
  error: string | null;
  connectToJob: (jobId: string) => void;
  resetSocketState: () => void;
}

export function useWebSocket(clientId: string): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState(0);
  const [eta, setEta] = useState(0);
  const [speed, setSpeed] = useState(0);
  const [phase, setPhase] = useState('Idle');
  const [logs, setLogs] = useState<string[]>([]);
  const [jobStatus, setJobStatus] = useState<JobStatus | 'IDLE'>('IDLE');
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const activeJobIdRef = useRef<string | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const reconnectAttemptsRef = useRef(0);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connect = useCallback((jobId: string) => {
    disconnect();
    activeJobIdRef.current = jobId;
    
    // Dynamically calculate WebSocket URL based on location
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
      ? '127.0.0.1:8000' 
      : window.location.host;
      
    const wsUrl = `${wsProto}//${host}/ws/jobs/${clientId}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        setError(null);
        setJobStatus('RUNNING');
        toast.success(`Connected to active calculation socket for Job ID: ${jobId.substring(0, 8)}...`, {
          icon: '🔌',
          style: { background: '#0B132B', color: '#06B6D4', border: '1px solid rgba(6, 182, 212, 0.2)' }
        });
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          if (msg.type === 'PING') {
            ws.send(JSON.stringify({ type: 'PONG' }));
            return;
          }
          
          if (msg.job_id !== activeJobIdRef.current) return;

          if (msg.type === 'PROGRESS' && msg.data) {
            const data: JobTelemetry = msg.data;
            setProgress(data.progress_pct);
            setEta(data.eta_seconds);
            setSpeed(data.compounds_per_sec);
            
            // Allow active_node to override phase display
            if (msg.data.active_node) {
              setPhase(msg.data.active_node);
            } else {
              setPhase(data.phase);
            }
            
            if (data.logs && data.logs.length > 0) {
              setLogs(prev => {
                // Merge logs unique by reference
                const newLogs = [...prev, ...data.logs];
                return Array.from(new Set(newLogs)).slice(-100); // Limit list buffer
              });
            }
          } else if (msg.type === 'JOB_COMPLETED') {
            setProgress(100);
            setJobStatus('COMPLETED');
            setPhase('Complete');
            toast.success('Computational toxicology job completed successfully!', {
              icon: '🏁',
              duration: 5000,
              style: { background: '#0B132B', color: '#10B981', border: '1px solid rgba(16, 185, 129, 0.2)' }
            });
            
            // Store the new lineage (field: 'lineage')
            if (msg.data && msg.data.lineage) {
              useWorkspaceStore.getState().setActiveLineage(msg.data.lineage);
            }
            // Keep backward compat: also handle old 'graph' field
            if (msg.data && msg.data.graph) {
              useWorkspaceStore.getState().setActiveSegregationResult(msg.data);
            }
            
            activeJobIdRef.current = null; // Prevent exponential reconnect loop
            disconnect();
          } else if (msg.type === 'JOB_FAILED') {
            setJobStatus('FAILED');
            setError(msg.error || 'Job execution failed');
            toast.error(`Job calculations failed: ${msg.error || 'Unknown Error'}`, {
              style: { background: '#0B132B', color: '#EF4444', border: '1px solid rgba(239, 68, 68, 0.2)' }
            });
            activeJobIdRef.current = null;
            disconnect();
          } else if (msg.type === 'JOB_CANCELLED') {
            setJobStatus('CANCELLED');
            toast('Job computations aborted by user.', {
              icon: '🛑',
              style: { background: '#0B132B', color: '#F59E0B', border: '1px solid rgba(245, 158, 11, 0.2)' }
            });
            activeJobIdRef.current = null;
            disconnect();
          }
        } catch (err) {
          console.error('Failed to parse socket message frame:', err);
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Exponential reconnect backoff if job is still running
        if (activeJobIdRef.current && reconnectAttemptsRef.current < 5) {
          const timeout = Math.pow(2, reconnectAttemptsRef.current) * 1000;
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connect(jobId);
          }, timeout);
        }
      };

    } catch (err: any) {
      setError(err.message || 'Failed to establish WebSocket connection');
    }
  }, [clientId, disconnect]);

  const connectToJob = useCallback((jobId: string) => {
    connect(jobId);
  }, [connect]);

  const resetSocketState = useCallback(() => {
    disconnect();
    activeJobIdRef.current = null;
    setProgress(0);
    setEta(0);
    setSpeed(0);
    setPhase('Idle');
    setLogs([]);
    setJobStatus('IDLE');
    setError(null);
  }, [disconnect]);

  useEffect(() => {
    return () => {
      disconnect();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [disconnect]);

  return {
    isConnected, progress, eta, speed, phase, logs, jobStatus, error,
    connectToJob, resetSocketState
  };
}

import { apiClient } from './apiClient';
import type { IngestResponse } from './uploadApi';

export interface TelemetryResponse {
  ram_usage_pct: number;
  cpu_usage_pct: number;
  cache_hit_rate_pct: number;
  total_cached_compounds: number;
  active_jobs_count: number;
  active_workspaces: number;
}

export const workspaceApi = {
  /**
   * Pre-seeds active user workspace with standard toxicology benchmark data.
   */
  loadDemoDataset: async (clientId: string): Promise<IngestResponse> => {
    const formData = new FormData();
    formData.append('client_id', clientId);

    const response = await apiClient.post<IngestResponse>('/api/demo_ingest', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Retrieves host telemetry diagnostics (memory shielding, worker logs, workspace size).
   */
  getTelemetry: async (abortSignal?: AbortSignal): Promise<TelemetryResponse> => {
    const response = await apiClient.get<TelemetryResponse>('/api/telemetry', {
      signal: abortSignal,
    });
    return response.data;
  },
};

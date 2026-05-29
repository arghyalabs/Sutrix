import { apiClient } from './apiClient';

export interface SubmitEnrichmentResponse {
  job_id: string;
  status: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  progress_pct: number;
  completed_items: number;
  total_items: number;
  error?: string;
}

export interface EnrichmentResultsResponse {
  job_id: string;
  total_rows: number;
  columns: string[];
  preview: any[];
  parquet_path: string;
}

export const enrichmentApi = {
  /**
   * Dispatches parallel QSAR calculations and PubChem API enrichment.
   */
  runEnrichment: async (
    selectedDescriptors: string[],
    includeMordred: boolean,
    mode: string,
    clientId: string
  ): Promise<SubmitEnrichmentResponse> => {
    const response = await apiClient.post<SubmitEnrichmentResponse>('/api/jobs/enrich', {
      client_id: clientId,
      selected_descriptors: selectedDescriptors,
      include_mordred: includeMordred,
      mode,
    });
    return response.data;
  },

  /**
   * Queries job state during batch tasks.
   */
  queryStatus: async (clientId: string): Promise<JobStatusResponse> => {
    const response = await apiClient.get<JobStatusResponse>(`/api/jobs/${clientId}/status`);
    return response.data;
  },

  /**
   * Requests cancellation of active background computations.
   */
  cancelJob: async (clientId: string): Promise<void> => {
    await apiClient.post(`/api/jobs/${clientId}/cancel`);
  },

  /**
   * Fetches available descriptors from RDKit and Mordred.
   */
  fetchAvailableDescriptors: async (): Promise<{ rdkit: string[]; mordred: string[] }> => {
    const response = await apiClient.get('/api/descriptors');
    return response.data;
  },

  /**
   * Retrieves final snappy Parquet results.
   */
  fetchResults: async (clientId: string): Promise<EnrichmentResultsResponse> => {
    const response = await apiClient.get<EnrichmentResultsResponse>(`/api/jobs/${clientId}/result`);
    return response.data;
  },
};

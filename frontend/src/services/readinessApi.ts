import { apiClient } from './apiClient';

export interface ReadinessResponse {
  score: number;
  tier: string;
  breakdown: {
    structural_completeness: number;
    endpoint_uniformity: number;
    potency_consistency: number;
  };
  deductions: string[];
  harmonized: boolean;
  findings: string[];
  pca?: any;
}

export const readinessApi = {
  /**
   * Triggers dataset audits and returns final scoring structures.
   */
  evaluateReadiness: async (clientId: string): Promise<ReadinessResponse> => {
    const response = await apiClient.post<ReadinessResponse>('/api/readiness', {
      client_id: clientId,
    });
    return response.data;
  },

  // ── Section-specific background job triggers ─────────────────────────────
  runPCA: (clientId: string) =>
    apiClient.post('/api/modeling/pca', { client_id: clientId }).then(r => r.data),
  runCorrelation: (clientId: string) =>
    apiClient.post('/api/modeling/correlation', { client_id: clientId }).then(r => r.data),
  runVariance: (clientId: string) =>
    apiClient.post('/api/modeling/variance', { client_id: clientId }).then(r => r.data),
  runCoverage: (clientId: string) =>
    apiClient.post('/api/modeling/coverage', { client_id: clientId }).then(r => r.data),
  runDomain: (clientId: string) =>
    apiClient.post('/api/modeling/domain', { client_id: clientId }).then(r => r.data),
  runOutliers: (clientId: string) =>
    apiClient.post('/api/modeling/outliers', { client_id: clientId }).then(r => r.data),
  runImbalance: (clientId: string) =>
    apiClient.post('/api/modeling/imbalance', { client_id: clientId }).then(r => r.data),
  runLeakage: (clientId: string) =>
    apiClient.post('/api/modeling/leakage', { client_id: clientId }).then(r => r.data),
  runOECD: (clientId: string) =>
    apiClient.post('/api/modeling/oecd', { client_id: clientId }).then(r => r.data),

  // ── Retrieve cached section results ──────────────────────────────────────
  getSectionResult: (clientId: string, section: string) =>
    apiClient.get(`/api/modeling/${clientId}/results/${section}`).then(r => r.data),
};


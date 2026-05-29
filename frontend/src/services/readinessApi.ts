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
};

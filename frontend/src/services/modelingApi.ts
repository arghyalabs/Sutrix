import { apiClient } from './apiClient';
import type { ModelingAnalysis } from '../types';

export const modelingApi = {
  runAnalysis: async (clientId: string): Promise<ModelingAnalysis> => {
    const { data } = await apiClient.post('/api/modeling/analyze', { client_id: clientId });
    return data;
  },

  getResults: async (clientId: string): Promise<ModelingAnalysis> => {
    const { data } = await apiClient.get(`/api/modeling/${clientId}/results`);
    return data;
  },

  exportReport: async (clientId: string, format: 'json' | 'csv' | 'xlsx'): Promise<Blob> => {
    const { data } = await apiClient.post(
      `/api/modeling/${clientId}/export?format=${format}`,
      {},
      { responseType: 'blob' }
    );
    return data;
  },

  getEmbedding: async (clientId: string): Promise<any> => {
    const { data } = await apiClient.get(`/api/modeling/${clientId}/embedding`);
    return data;
  },
};

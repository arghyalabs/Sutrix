import { apiClient } from './apiClient';

export interface SchemaInference {
  column: string;
  mapped_to: string;
  confidence: number;
  reasons: string[];
}

export interface SchemaInferResponse {
  mappings: SchemaInference[];
}

export interface SaveMappingResponse {
  success: boolean;
  mappings: Record<string, string>;
  columns: string[];
  dataset_type?: string;
  warnings?: string[];
}

export const mappingApi = {
  /**
   * Dispatches column list to AI inference engine.
   */
  inferSchema: async (columns: string[], abortSignal?: AbortSignal): Promise<SchemaInferResponse> => {
    const response = await apiClient.post<SchemaInferResponse>('/api/schema/infer', {
      columns,
    }, { signal: abortSignal });
    return response.data;
  },

  /**
   * Confirms and applies chemical variable mapping schemas.
   */
  saveMappings: async (mappings: Record<string, string>, clientId: string): Promise<SaveMappingResponse> => {
    const response = await apiClient.post<SaveMappingResponse>('/api/mapping', {
      client_id: clientId,
      mappings,
    });
    return response.data;
  },
};

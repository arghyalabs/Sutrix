import { apiClient } from './apiClient';

export interface IngestResponse {
  success: boolean;
  filename: string;
  row_count: number;
  columns: string[];
  preview: any[];
  parquet_path: string;
}

export interface CurateResponse {
  success: boolean;
  row_count: number;
  columns: string[];
  preview: any[];
  parquet_path: string;
}

export const uploadApi = {
  /**
   * Uploads raw chemical dataset to FastAPI snappy ingestion pipeline.
   */
  ingestFile: async (file: File, clientId: string): Promise<IngestResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('client_id', clientId);

    const response = await apiClient.post<IngestResponse>('/api/ingest', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000, // 2 minutes timeout for large datasets processing
    });
    return response.data;
  },

  /**
   * Drops user-specified metadata columns.
   */
  curateColumns: async (colsToDrop: string[], clientId: string): Promise<CurateResponse> => {
    const response = await apiClient.post<CurateResponse>('/api/curate', {
      client_id: clientId,
      columns_to_drop: colsToDrop,
    });
    return response.data;
  },
};

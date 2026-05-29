import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const hierarchyApi = {
  getTree: async (clientId: string) => {
    const res = await axios.get(`${BASE_URL}/api/hierarchy/${clientId}/tree`);
    return res.data;
  },
  getNodeDetail: async (clientId: string, nodeId: string) => {
    const res = await axios.get(`${BASE_URL}/api/hierarchy/${clientId}/node/${nodeId}`);
    return res.data;
  },
  exportNode: (clientId: string, nodeId: string, format: string) => {
    window.open(`${BASE_URL}/api/hierarchy/${clientId}/export/${nodeId}?format=${format}`, '_blank');
  },
  exportAll: async (clientId: string) => {
    const res = await axios.get(`${BASE_URL}/api/hierarchy/${clientId}/export-all`, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `scientific_dataset_${clientId}.zip`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};

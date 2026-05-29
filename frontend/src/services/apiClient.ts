import axios from 'axios';
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000, // 30 seconds standard timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Configure automatic retry rules
interface RetryConfig extends InternalAxiosRequestConfig {
  _retryCount?: number;
}

apiClient.interceptors.request.use(
  (config) => {
    // Add additional request telemetry or security tokens if required in production
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryConfig;
    if (!config) return Promise.reject(error);

    config._retryCount = config._retryCount ?? 0;
    const maxRetries = 3;

    // Retry only on network drops or 5xx server exceptions
    const isNetworkError = !error.response;
    const isServerError = error.response && error.response.status >= 500;

    if ((isNetworkError || isServerError) && config._retryCount < maxRetries) {
      config._retryCount += 1;
      const delay = Math.pow(2, config._retryCount) * 1000; // Exponential backoff (2s, 4s, 8s)
      
      console.warn(
        `API Transport Warning: Retrying request to ${config.url} (${config._retryCount}/${maxRetries}) in ${delay}ms...`
      );
      
      await new Promise((resolve) => setTimeout(resolve, delay));
      return apiClient(config);
    }

    return Promise.reject(error);
  }
);

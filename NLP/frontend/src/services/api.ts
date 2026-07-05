import axios, { AxiosError, AxiosProgressEvent } from 'axios';
import type {
  Dataset,
  DatasetListItem,
  DatasetUploadResponse,
  QueryRequest,
  QueryResult,
  SQLQueryRequest,
  AnalyticsResult,
  CorrelationData,
  TimeSeriesData,
  Dashboard,
  DashboardListItem,
  NLPDashboardRequest,
  Report,
  ReportListItem,
  ReportGenerateRequest,
} from '../types';

// ─── Axios Instance ───────────────────────────────────────────────────────────

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 60000,
});

// ─── Request Interceptor ──────────────────────────────────────────────────────

apiClient.interceptors.request.use(
  (config) => {
    if (!config.headers['Content-Type'] && !(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response Interceptor ─────────────────────────────────────────────────────

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    let message = 'An unexpected error occurred. Please try again.';

    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as Record<string, unknown>;

      if (status === 400) {
        message = (data?.detail as string) || (data?.message as string) || 'Bad request. Please check your input.';
      } else if (status === 401) {
        message = 'Unauthorized. Please log in again.';
      } else if (status === 403) {
        message = 'Access denied. You do not have permission to perform this action.';
      } else if (status === 404) {
        message = (data?.detail as string) || 'Resource not found.';
      } else if (status === 422) {
        const detail = data?.detail;
        if (Array.isArray(detail)) {
          message = detail.map((d: Record<string, unknown>) => d.msg).join('; ');
        } else {
          message = (detail as string) || 'Validation error. Please check your input.';
        }
      } else if (status === 500) {
        message = 'Internal server error. Please try again later.';
      } else if (status === 503) {
        message = 'Service temporarily unavailable. Please try again later.';
      }
    } else if (error.request) {
      message = 'Cannot connect to server. Please ensure the backend is running on http://localhost:8000.';
    } else {
      message = error.message || message;
    }

    const enrichedError = new Error(message) as Error & { originalError: AxiosError; statusCode?: number };
    enrichedError.originalError = error;
    enrichedError.statusCode = error.response?.status;
    return Promise.reject(enrichedError);
  }
);

// ─── Dataset APIs ─────────────────────────────────────────────────────────────

export const uploadDataset = async (
  file: File,
  name: string,
  onProgress?: (progress: number) => void
): Promise<DatasetUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('name', name);

  const response = await apiClient.post<DatasetUploadResponse>('/datasets/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
      if (progressEvent.total && onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
};

export const getDatasets = async (): Promise<DatasetListItem[]> => {
  const response = await apiClient.get<DatasetListItem[]>('/datasets');
  return response.data;
};

export const getDataset = async (id: string): Promise<Dataset> => {
  const response = await apiClient.get<Dataset>(`/datasets/${id}`);
  return response.data;
};

export const deleteDataset = async (id: string): Promise<void> => {
  await apiClient.delete(`/datasets/${id}`);
};

export const pollDatasetStatus = async (
  id: string,
  onStatusChange: (status: string) => void,
  maxAttempts = 60,
  intervalMs = 2000
): Promise<Dataset> => {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const poll = async () => {
      try {
        const dataset = await getDataset(id);
        onStatusChange(dataset.status);
        if (dataset.status === 'ready') {
          resolve(dataset);
          return;
        }
        if (dataset.status === 'error') {
          reject(new Error('Dataset processing failed.'));
          return;
        }
        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error('Dataset processing timed out. Please try again.'));
          return;
        }
        setTimeout(poll, intervalMs);
      } catch (err) {
        reject(err);
      }
    };
    poll();
  });
};

// ─── Query APIs ───────────────────────────────────────────────────────────────

export const nlpQuery = async (datasetId: string, query: string, limit = 500): Promise<QueryResult> => {
  const payload: QueryRequest = { dataset_id: datasetId, query, limit };
  const response = await apiClient.post<QueryResult>('/query/nlp', payload);
  return response.data;
};

export const executeSQL = async (datasetId: string, sql: string, limit = 500): Promise<QueryResult> => {
  const payload: SQLQueryRequest = { dataset_id: datasetId, sql, limit };
  const response = await apiClient.post<QueryResult>('/query/sql', payload);
  return response.data;
};

// ─── Analytics APIs ───────────────────────────────────────────────────────────

export const getAnalytics = async (datasetId: string): Promise<AnalyticsResult> => {
  const response = await apiClient.get<AnalyticsResult>(`/analytics/${datasetId}/summary`);
  return response.data;
};

export const getCorrelations = async (datasetId: string): Promise<CorrelationData> => {
  const response = await apiClient.get<CorrelationData>(`/analytics/${datasetId}/correlations`);
  return response.data;
};

export const getTimeSeries = async (
  datasetId: string,
  dateCol: string,
  valueCol: string,
  freq = 'M'
): Promise<TimeSeriesData> => {
  const response = await apiClient.get<TimeSeriesData>(
    `/analytics/${datasetId}/timeseries?date_col=${encodeURIComponent(dateCol)}&value_col=${encodeURIComponent(valueCol)}&freq=${freq}`
  );
  return response.data;
};

// ─── Dashboard APIs ───────────────────────────────────────────────────────────

export const getDashboards = async (): Promise<DashboardListItem[]> => {
  const response = await apiClient.get<DashboardListItem[]>('/dashboards');
  return response.data;
};

export const getDashboard = async (id: string): Promise<Dashboard> => {
  const response = await apiClient.get<Dashboard>(`/dashboards/${id}`);
  return response.data;
};

export const createDashboard = async (data: Partial<Dashboard>): Promise<Dashboard> => {
  const response = await apiClient.post<Dashboard>('/dashboards', data);
  return response.data;
};

export const updateDashboard = async (id: string, data: Partial<Dashboard>): Promise<Dashboard> => {
  const response = await apiClient.put<Dashboard>(`/dashboards/${id}`, data);
  return response.data;
};

export const deleteDashboard = async (id: string): Promise<void> => {
  await apiClient.delete(`/dashboards/${id}`);
};

export const generateDashboardFromNLP = async (
  prompt: string,
  datasetId: string,
  dashboardName?: string
): Promise<Dashboard> => {
  const payload: NLPDashboardRequest = {
    prompt,
    dataset_id: datasetId,
    dashboard_name: dashboardName,
  };
  const response = await apiClient.post<Dashboard>('/dashboards/generate', payload);
  return response.data;
};

// ─── Report APIs ──────────────────────────────────────────────────────────────

export const getReports = async (): Promise<ReportListItem[]> => {
  const response = await apiClient.get<ReportListItem[]>('/reports');
  return response.data;
};

export const getReport = async (id: string): Promise<Report> => {
  const response = await apiClient.get<Report>(`/reports/${id}`);
  return response.data;
};

export const createReport = async (data: Partial<Report>): Promise<Report> => {
  const response = await apiClient.post<Report>('/reports', data);
  return response.data;
};

export const generateReport = async (datasetId: string, config: ReportGenerateRequest): Promise<Report> => {
  const response = await apiClient.post<Report>('/reports/generate', {
    ...config,
    dataset_id: datasetId,
  });
  return response.data;
};

export const exportReportCSV = async (reportId: string): Promise<Blob> => {
  const response = await apiClient.get(`/reports/${reportId}/export/csv`, {
    responseType: 'blob',
  });
  return response.data as Blob;
};

export const exportReportPDF = async (reportId: string): Promise<Blob> => {
  const response = await apiClient.get(`/reports/${reportId}/export/pdf`, {
    responseType: 'blob',
  });
  return response.data as Blob;
};

export const deleteReport = async (id: string): Promise<void> => {
  await apiClient.delete(`/reports/${id}`);
};

// ─── Utility ──────────────────────────────────────────────────────────────────

export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export default apiClient;

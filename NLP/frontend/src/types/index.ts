// ─── Dataset Types ────────────────────────────────────────────────────────────

export type DatasetStatus = 'uploading' | 'processing' | 'ready' | 'error';

export interface DatasetColumn {
  name: string;
  dtype: string;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  sample_values: (string | number | null)[];
  min_value?: number | string | null;
  max_value?: number | string | null;
  mean_value?: number | null;
  std_value?: number | null;
}

export interface Dataset {
  id: string;
  name: string;
  filename: string;
  file_size: number;
  file_type: string;
  row_count: number;
  column_count: number;
  columns: DatasetColumn[];
  status: DatasetStatus;
  created_at: string;
  updated_at: string;
  preview_data?: Record<string, unknown>[];
  health_score?: number;
  description?: string;
}

export interface DatasetListItem {
  id: string;
  name: string;
  filename: string;
  file_size: number;
  file_type: string;
  row_count: number;
  column_count: number;
  status: DatasetStatus;
  created_at: string;
  updated_at: string;
  health_score?: number;
}

export interface DatasetUploadResponse {
  dataset_id: string;
  status: DatasetStatus;
  message: string;
}

// ─── Query Types ──────────────────────────────────────────────────────────────

export type QueryIntent =
  | 'aggregation'
  | 'filter'
  | 'comparison'
  | 'trend'
  | 'distribution'
  | 'correlation'
  | 'ranking'
  | 'unknown';

export type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'area' | 'metric' | 'table';

export interface QueryRequest {
  dataset_id: string;
  query: string;
  limit?: number;
}

export interface SQLQueryRequest {
  dataset_id: string;
  sql: string;
  limit?: number;
}

export interface QueryColumn {
  name: string;
  dtype: string;
}

export interface QueryResult {
  query_id: string;
  dataset_id: string;
  original_query: string;
  generated_sql: string;
  intent: QueryIntent;
  entities: Record<string, string[]>;
  columns: QueryColumn[];
  data: Record<string, unknown>[];
  row_count: number;
  execution_time_ms: number;
  chart_recommendation: ChartType;
  chart_config?: ChartConfig;
  created_at: string;
}

export interface ChartConfig {
  x_axis?: string;
  y_axis?: string;
  series?: string[];
  color_by?: string;
  title?: string;
  aggregation?: string;
}

// ─── Analytics Types ──────────────────────────────────────────────────────────

export interface ColumnStats {
  column: string;
  dtype: string;
  count: number;
  null_count: number;
  null_pct: number;
  unique_count: number;
  min?: number | string;
  max?: number | string;
  mean?: number;
  std?: number;
  median?: number;
  q25?: number;
  q75?: number;
  top_values?: { value: string | number; count: number; percentage: number }[];
}

export interface AnalyticsResult {
  dataset_id: string;
  row_count: number;
  column_count: number;
  memory_usage_mb: number;
  health_score: number;
  column_stats: ColumnStats[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  duplicate_rows: number;
  created_at: string;
}

export interface CorrelationData {
  dataset_id: string;
  columns: string[];
  matrix: number[][];
  strong_correlations: {
    col1: string;
    col2: string;
    coefficient: number;
  }[];
}

export interface TimeSeriesData {
  dataset_id: string;
  date_column: string;
  value_column: string;
  frequency: string;
  data: {
    date: string;
    value: number;
    trend?: number;
  }[];
}

export interface DistributionData {
  dataset_id: string;
  column: string;
  dtype: string;
  bins?: { bin_start: number; bin_end: number; count: number; percentage: number }[];
  categories?: { value: string; count: number; percentage: number }[];
}

// ─── Dashboard Types ──────────────────────────────────────────────────────────

export interface WidgetPosition {
  x: number;
  y: number;
  w: number;
  h: number;
  i: string;
}

export type WidgetType = 'chart' | 'table' | 'metric' | 'text';

export interface DashboardWidget {
  id: string;
  title: string;
  widget_type: WidgetType;
  chart_type?: ChartType;
  dataset_id?: string;
  query?: string;
  sql?: string;
  query_result?: QueryResult;
  position: WidgetPosition;
  config?: Record<string, unknown>;
  refresh_interval?: number;
}

export interface Dashboard {
  id: string;
  name: string;
  description?: string;
  widgets: DashboardWidget[];
  created_at: string;
  updated_at: string;
  is_public: boolean;
  tags?: string[];
}

export interface DashboardListItem {
  id: string;
  name: string;
  description?: string;
  widget_count: number;
  created_at: string;
  updated_at: string;
  is_public: boolean;
  tags?: string[];
}

export interface NLPDashboardRequest {
  prompt: string;
  dataset_id: string;
  dashboard_name?: string;
}

// ─── Report Types ─────────────────────────────────────────────────────────────

export type ReportSectionType =
  | 'summary'
  | 'chart'
  | 'table'
  | 'correlation'
  | 'distribution'
  | 'timeseries'
  | 'custom';

export interface ReportSection {
  id: string;
  title: string;
  section_type: ReportSectionType;
  content?: string;
  chart_type?: ChartType;
  data?: Record<string, unknown>[];
  chart_config?: ChartConfig;
  order: number;
}

export interface Report {
  id: string;
  name: string;
  description?: string;
  dataset_id: string;
  dataset_name?: string;
  sections: ReportSection[];
  created_at: string;
  updated_at: string;
  status: 'draft' | 'generating' | 'ready' | 'error';
}

export interface ReportListItem {
  id: string;
  name: string;
  description?: string;
  dataset_id: string;
  dataset_name?: string;
  section_count: number;
  created_at: string;
  updated_at: string;
  status: 'draft' | 'generating' | 'ready' | 'error';
}

export interface ReportGenerateRequest {
  dataset_id: string;
  name: string;
  description?: string;
  nlp_prompt?: string;
  section_types?: ReportSectionType[];
}

// ─── UI / App Types ───────────────────────────────────────────────────────────

export interface SnackbarMessage {
  id: string;
  message: string;
  severity: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

export interface QueryHistoryItem {
  id: string;
  query: string;
  dataset_id: string;
  dataset_name: string;
  timestamp: string;
  result_count?: number;
}

export interface AppStats {
  total_datasets: number;
  total_queries: number;
  active_dashboards: number;
  reports_generated: number;
}

export interface ActivityItem {
  id: string;
  type: 'upload' | 'query' | 'dashboard' | 'report';
  title: string;
  subtitle: string;
  timestamp: string;
}

// ─── API Response Wrapper ─────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  message: string;
  detail?: string;
  status_code?: number;
}

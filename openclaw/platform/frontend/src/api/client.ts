// Axios API client with JWT injection + 401 handling.
import axios, { AxiosInstance } from "axios";
import type {
  Agent,
  Approval,
  AuditEntry,
  Dashboard,
  Execution,
  NodeCatalog,
  TokenResponse,
  ToolManifest,
  Workflow,
} from "./types";

const TOKEN_KEY = "clawflow_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "",
});

api.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && !location.pathname.includes("/login")) {
      tokenStore.clear();
      location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export const Api = {
  // auth
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/api/auth/login", { email, password }).then((r) => r.data),
  me: () => api.get("/api/auth/me").then((r) => r.data),

  // tools
  tools: (q?: string) =>
    api.get<ToolManifest[]>("/api/tools", { params: { q } }).then((r) => r.data),
  nodeCatalog: () => api.get<NodeCatalog>("/api/tools/catalog/nodes").then((r) => r.data),
  refreshTools: () => api.post("/api/tools/refresh").then((r) => r.data),
  executeTool: (tool_id: string, inputs: Record<string, unknown>) =>
    api.post("/api/tools/execute", { tool_id, inputs }).then((r) => r.data),

  // workflows
  workflows: () => api.get<Workflow[]>("/api/workflows").then((r) => r.data),
  workflow: (id: string) => api.get<Workflow>(`/api/workflows/${id}`).then((r) => r.data),
  createWorkflow: (wf: Partial<Workflow>) =>
    api.post<Workflow>("/api/workflows", wf).then((r) => r.data),
  updateWorkflow: (id: string, wf: Partial<Workflow>) =>
    api.put<Workflow>(`/api/workflows/${id}`, wf).then((r) => r.data),
  deleteWorkflow: (id: string) => api.delete(`/api/workflows/${id}`).then((r) => r.data),
  runWorkflow: (id: string) =>
    api.post(`/api/workflows/${id}/run`, {}).then((r) => r.data),
  validateWorkflow: (id: string) =>
    api.get(`/api/workflows/${id}/validate`).then((r) => r.data),
  generateWorkflow: (prompt: string) =>
    api.post<Workflow>("/api/workflows/generate", { prompt }).then((r) => r.data),

  // executions
  executions: () => api.get<Execution[]>("/api/executions").then((r) => r.data),
  execution: (id: string) => api.get<Execution>(`/api/executions/${id}`).then((r) => r.data),
  cancelExecution: (id: string) =>
    api.post(`/api/executions/${id}/cancel`).then((r) => r.data),

  // agents
  agents: () => api.get<Agent[]>("/api/agents").then((r) => r.data),
  createAgent: (a: Partial<Agent>) => api.post<Agent>("/api/agents", a).then((r) => r.data),
  updateAgent: (id: string, a: Partial<Agent>) =>
    api.put<Agent>(`/api/agents/${id}`, a).then((r) => r.data),
  deleteAgent: (id: string) => api.delete(`/api/agents/${id}`).then((r) => r.data),

  // approvals
  approvals: (status?: string) =>
    api.get<Approval[]>("/api/approvals", { params: { status } }).then((r) => r.data),
  respondApproval: (approval_id: string, decision: string, comment?: string) =>
    api.post("/api/approvals/respond", { approval_id, decision, comment }).then((r) => r.data),

  // audit + monitoring
  audit: (limit = 200) =>
    api.get<AuditEntry[]>("/api/audit", { params: { limit } }).then((r) => r.data),
  dashboard: () => api.get<Dashboard>("/api/monitoring/dashboard").then((r) => r.data),
  timeline: () => api.get("/api/monitoring/timeline").then((r) => r.data),

  // settings + chatbot
  settings: () => api.get("/api/settings").then((r) => r.data),
  updateSettings: (s: Record<string, unknown>) =>
    api.put("/api/settings", s).then((r) => r.data),
  chat: (message: string) => api.post("/api/chat", { message }).then((r) => r.data),
};

export default api;

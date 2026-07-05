import axios, { AxiosInstance } from "axios";

const BASE_URL = "/api";

function createClient(): AxiosInstance {
  const client = axios.create({ baseURL: BASE_URL });

  client.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });

  client.interceptors.response.use(
    (r) => r,
    (err) => {
      if (err.response?.status === 401) {
        localStorage.clear();
        window.location.href = "/login";
      }
      return Promise.reject(err);
    }
  );

  return client;
}

export const api = createClient();

// ── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),
  me: () => api.get("/auth/me"),
};

// ── Chat ─────────────────────────────────────────────────────────────────────

export const chatApi = {
  sendMessage: (conversationId: string, message: string) =>
    api.post(`/chat/${conversationId}/message`, { message }),
  getHistory: (conversationId: string) =>
    api.get(`/chat/${conversationId}/history`),
};

// ── Admin ─────────────────────────────────────────────────────────────────────

export const adminApi = {
  getApiKeys: () => api.get("/admin/api-keys"),
  updateApiKeys: (keys: Record<string, string>) => api.put("/admin/api-keys", keys),

  getSystemConfig: () => api.get("/admin/system-config"),
  updateSystemConfig: (config: object) => api.put("/admin/system-config", config),

  getGuardrails: () => api.get("/admin/guardrails"),
  updateGuardrails: (guardrails: object) => api.put("/admin/guardrails", guardrails),

  listConversations: (skip = 0, limit = 50) =>
    api.get(`/admin/conversations?skip=${skip}&limit=${limit}`),
  getConversation: (id: string) => api.get(`/admin/conversations/${id}`),
  getAnalytics: (id: string) => api.get(`/admin/conversations/${id}/analytics`),
  getSummary: (id: string) => api.get(`/admin/conversations/${id}/summary`),
  getInsights: (id: string) => api.get(`/admin/conversations/${id}/insights`),
};

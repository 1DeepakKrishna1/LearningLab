import axios from "axios";

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("ialloc_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("ialloc_token");
      localStorage.removeItem("ialloc_user");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export const apiError = (err) =>
  err?.response?.data?.detail
    ? typeof err.response.data.detail === "string"
      ? err.response.data.detail
      : JSON.stringify(err.response.data.detail)
    : err.message || "Request failed";

export default api;

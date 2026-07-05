// Thin client for the RESTAPI AI Agent backend.

async function request(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (resp.status === 204) return null;
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || `Request failed (${resp.status})`);
  }
  return data;
}

export const api = {
  health: () => request("/api/health"),

  listSpecs: () => request("/api/specs"),

  ingestUrl: (url, baseUrlOverride) =>
    request("/api/specs", {
      method: "POST",
      body: JSON.stringify({ url, base_url_override: baseUrlOverride || null }),
    }),

  ingestText: (content, filename, baseUrlOverride) =>
    request("/api/specs/upload", {
      method: "POST",
      body: JSON.stringify({
        content,
        filename: filename || null,
        base_url_override: baseUrlOverride || null,
      }),
    }),

  refreshSpec: (specId) =>
    request(`/api/specs/${specId}/refresh`, { method: "POST" }),

  deleteSpec: (specId) =>
    request(`/api/specs/${specId}`, { method: "DELETE" }),

  listOperations: (specId, q) =>
    request(`/api/specs/${specId}/operations${q ? `?q=${encodeURIComponent(q)}` : ""}`),

  chat: (payload) =>
    request("/api/chat", { method: "POST", body: JSON.stringify(payload) }),

  approve: (payload) =>
    request("/api/chat/approve", { method: "POST", body: JSON.stringify(payload) }),
};

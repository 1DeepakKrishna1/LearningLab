import React, { useEffect } from "react";

// Lets the user supply credentials the backend injects into outbound calls.
export default function AuthPanel({ auth, setAuth, schemes }) {
  const set = (patch) => setAuth({ ...auth, ...patch });

  // Prefill the header/query name from the spec's declared apiKey scheme so it
  // can't be confused with the key value (a common mistake that produces an
  // "illegal header name" error when, e.g., an email is typed into this field).
  const apiKeyScheme = (schemes || []).find((s) => s.type === "apiKey");
  useEffect(() => {
    if (auth.type === "api_key" && apiKeyScheme?.header_name && !auth.api_key_name) {
      set({
        api_key_name: apiKeyScheme.header_name,
        api_key_location: apiKeyScheme.location === "query" ? "query" : "header",
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.type, apiKeyScheme?.header_name]);

  return (
    <section className="panel">
      <h3>Authentication</h3>
      {schemes?.length > 0 && (
        <p className="muted small">
          Spec declares: {schemes.map((s) => `${s.name} (${s.type})`).join(", ")}
        </p>
      )}

      <select className="input" value={auth.type} onChange={(e) => set({ type: e.target.value })}>
        <option value="none">No auth</option>
        <option value="api_key">API Key</option>
        <option value="bearer">Bearer / JWT</option>
        <option value="basic">Basic</option>
      </select>

      {auth.type === "api_key" && (
        <>
          <label className="field-label">Header/query name</label>
          <input
            className="input"
            placeholder="e.g. X-API-Key"
            value={auth.api_key_name}
            onChange={(e) => set({ api_key_name: e.target.value })}
          />
          <label className="field-label">Key value</label>
          <input
            className="input"
            type="password"
            placeholder="the secret API key string"
            value={auth.api_key}
            onChange={(e) => set({ api_key: e.target.value })}
          />
          <select
            className="input"
            value={auth.api_key_location}
            onChange={(e) => set({ api_key_location: e.target.value })}
          >
            <option value="header">In header</option>
            <option value="query">In query string</option>
          </select>
        </>
      )}

      {auth.type === "bearer" && (
        <>
          <label className="field-label">
            Access token (sent as <code>Authorization: Bearer …</code>)
          </label>
          <input
            className="input"
            type="password"
            placeholder="paste the access_token from /auth/login"
            value={auth.token}
            onChange={(e) => set({ token: e.target.value })}
          />
        </>
      )}

      {auth.type === "basic" && (
        <>
          <input
            className="input"
            placeholder="Username"
            value={auth.username}
            onChange={(e) => set({ username: e.target.value })}
          />
          <input
            className="input"
            type="password"
            placeholder="Password"
            value={auth.password}
            onChange={(e) => set({ password: e.target.value })}
          />
        </>
      )}
    </section>
  );
}

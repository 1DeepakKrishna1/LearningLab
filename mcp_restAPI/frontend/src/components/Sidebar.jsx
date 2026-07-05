import React, { useState } from "react";
import { api } from "../api.js";
import AuthPanel from "./AuthPanel.jsx";

export default function Sidebar({
  health,
  specs,
  activeSpec,
  auth,
  setAuth,
  onSelect,
  onRefreshList,
  onError,
}) {
  const [mode, setMode] = useState("url"); // "url" | "paste"
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [baseOverride, setBaseOverride] = useState("");
  const [importing, setImporting] = useState(false);

  const doImport = async () => {
    setImporting(true);
    onError(null);
    try {
      let spec;
      if (mode === "url") {
        if (!url.trim()) throw new Error("Enter a spec URL.");
        spec = await api.ingestUrl(url.trim(), baseOverride.trim());
      } else {
        if (!text.trim()) throw new Error("Paste spec JSON/YAML.");
        spec = await api.ingestText(text, "pasted-spec", baseOverride.trim());
      }
      await onRefreshList();
      onSelect(spec);
      setUrl("");
      setText("");
    } catch (e) {
      onError(e.message);
    } finally {
      setImporting(false);
    }
  };

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    onError(null);
    try {
      const content = await file.text();
      const spec = await api.ingestText(content, file.name, baseOverride.trim());
      await onRefreshList();
      onSelect(spec);
    } catch (err) {
      onError(err.message);
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  };

  const removeSpec = async (specId, ev) => {
    ev.stopPropagation();
    try {
      await api.deleteSpec(specId);
      const list = await onRefreshList();
      if (activeSpec?.id === specId) onSelect(list[0] || null);
    } catch (e) {
      onError(e.message);
    }
  };

  const refreshSpec = async (specId, ev) => {
    ev.stopPropagation();
    try {
      await api.refreshSpec(specId);
      await onRefreshList();
    } catch (e) {
      onError(e.message);
    }
  };

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="logo">⚡</span>
        <div>
          <strong>RESTAPI AI Agent</strong>
          <div className="muted small">OpenAPI → natural language</div>
        </div>
      </div>

      <section className="panel">
        <h3>Import a spec</h3>
        <div className="tabs">
          <button className={mode === "url" ? "active" : ""} onClick={() => setMode("url")}>
            URL
          </button>
          <button className={mode === "paste" ? "active" : ""} onClick={() => setMode("paste")}>
            Paste / File
          </button>
        </div>

        {mode === "url" ? (
          <input
            className="input"
            placeholder="https://petstore3.swagger.io/api/v3/openapi.json"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        ) : (
          <>
            <textarea
              className="input textarea"
              placeholder="Paste OpenAPI JSON or YAML…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <label className="file-label">
              …or choose a file
              <input type="file" accept=".json,.yaml,.yml" onChange={onFile} hidden />
            </label>
          </>
        )}

        <input
          className="input"
          placeholder="Base URL override (optional)"
          value={baseOverride}
          onChange={(e) => setBaseOverride(e.target.value)}
        />
        <button className="btn primary full" onClick={doImport} disabled={importing}>
          {importing ? "Importing…" : "Import"}
        </button>
      </section>

      <section className="panel">
        <h3>Loaded specs</h3>
        {specs.length === 0 && <p className="muted small">No specs imported yet.</p>}
        <ul className="spec-list">
          {specs.map((s) => (
            <li
              key={s.id}
              className={activeSpec?.id === s.id ? "spec active" : "spec"}
              onClick={() => onSelect(s)}
            >
              <div className="spec-main">
                <strong>{s.title}</strong>
                <span className="muted small">
                  v{s.version || "?"} · OpenAPI {s.openapi_version} · {s.operation_count} ops
                </span>
              </div>
              <div className="spec-actions">
                {s.source?.startsWith("http") && (
                  <button title="Refresh" onClick={(e) => refreshSpec(s.id, e)}>
                    ↻
                  </button>
                )}
                <button title="Delete" onClick={(e) => removeSpec(s.id, e)}>
                  ✕
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {activeSpec && (
        <AuthPanel auth={auth} setAuth={setAuth} schemes={activeSpec.security_schemes} />
      )}

      <div className="sidebar-footer muted small">
        {health?.status === "ok" ? "Backend connected" : "Backend unreachable"}
      </div>
    </aside>
  );
}

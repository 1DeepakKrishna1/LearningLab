import React, { useState } from "react";

const METHOD_COLORS = {
  GET: "#2563eb",
  POST: "#16a34a",
  PUT: "#d97706",
  PATCH: "#9333ea",
  DELETE: "#dc2626",
};

function pretty(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

// Collapsible record of one executed REST call.
export default function ApiCallCard({ call }) {
  const [open, setOpen] = useState(false);
  const ok = call.ok;
  return (
    <div className={`call-card ${ok ? "ok" : "fail"}`}>
      <div className="call-head" onClick={() => setOpen((o) => !o)}>
        <span className="method" style={{ background: METHOD_COLORS[call.method] || "#475569" }}>
          {call.method}
        </span>
        <span className="call-url">{call.url}</span>
        <span className={`status ${ok ? "ok" : "fail"}`}>
          {call.status_code ?? "ERR"}
        </span>
        {call.duration_ms != null && <span className="muted small">{call.duration_ms} ms</span>}
        <span className="chevron">{open ? "▾" : "▸"}</span>
      </div>
      {open && (
        <div className="call-body">
          {call.error && <div className="call-error">{call.error}</div>}
          {call.request_body != null && (
            <>
              <div className="call-label">Request body</div>
              <pre>{pretty(call.request_body)}</pre>
            </>
          )}
          {call.response_preview != null && call.response_preview !== "" && (
            <>
              <div className="call-label">Response</div>
              <pre>{pretty(call.response_preview)}</pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}

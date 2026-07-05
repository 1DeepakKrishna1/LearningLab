import React, { useState } from "react";

function pretty(value) {
  if (value === null || value === undefined) return "(none)";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

// Human-in-the-loop gate shown before a mutating call executes.
export default function ApprovalModal({ approval, busy, onApprove, onReject }) {
  const [reason, setReason] = useState("");
  const isDelete = approval.method === "DELETE";

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>
          {isDelete ? "⚠️ Irreversible action" : "Approval required"}
        </h2>
        <p className="muted">{approval.reason}</p>

        <div className="approval-call">
          <span className="method" data-method={approval.method}>
            {approval.method}
          </span>
          <code>{approval.url}</code>
        </div>
        <p className="muted small">{approval.summary}</p>

        {approval.query && Object.keys(approval.query).length > 0 && (
          <>
            <div className="call-label">Query</div>
            <pre>{pretty(approval.query)}</pre>
          </>
        )}
        {approval.body != null && (
          <>
            <div className="call-label">Request body</div>
            <pre>{pretty(approval.body)}</pre>
          </>
        )}

        <input
          className="input"
          placeholder="Optional note (sent to the agent if you reject)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />

        <div className="modal-actions">
          <button className="btn ghost" disabled={busy} onClick={() => onReject(reason)}>
            Reject
          </button>
          <button className="btn primary" disabled={busy} onClick={onApprove}>
            {busy ? "Working…" : "Approve & run"}
          </button>
        </div>
      </div>
    </div>
  );
}

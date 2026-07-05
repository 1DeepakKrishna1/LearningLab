import { useState } from "react";
import api, { apiError } from "../api/client.js";

/**
 * Reusable AI assistant. Renders only when the stage has AI enabled.
 * Calls POST /api/ai/assist which routes to the Groq task configured by the
 * SystemAdmin for this stage.
 */
export default function AIAssist({ systemId, stage, applicationId, placeholder }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  if (!stage?.ai_enabled && !stage?.ai?.enabled) return null;

  async function run() {
    setBusy(true);
    setErr("");
    setOut("");
    try {
      const { data } = await api.post("/ai/assist", {
        system_id: systemId,
        stage_key: stage.key,
        application_id: applicationId || null,
        user_input: input,
      });
      setOut(data.content);
    } catch (e) {
      setErr(apiError(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ai-panel" style={{ marginTop: 14 }}>
      <h3>✨ AI Assist — {stage.name}</h3>
      {!open ? (
        <button className="ghost btn-sm" onClick={() => setOpen(true)}>
          Open AI assistant
        </button>
      ) : (
        <>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder || "Ask the AI to help with this stage…"}
          />
          <div className="row" style={{ marginTop: 8 }}>
            <button onClick={run} disabled={busy}>
              {busy ? "Thinking…" : "Run AI"}
            </button>
            <button className="secondary btn-sm" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
          {err && <div className="error">{err}</div>}
          {out && <div className="ai-output">{out}</div>}
        </>
      )}
    </div>
  );
}

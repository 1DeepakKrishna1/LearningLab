import { useEffect, useState } from "react";
import Layout from "../../components/Layout.jsx";
import { Badge, Empty } from "../../components/ui.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import api, { apiError } from "../../api/client.js";

export default function AILogs() {
  const { user } = useAuth();
  const sid = user.system_id;
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState(null);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState(null);

  useEffect(() => {
    if (!sid) return;
    api.get("/ai/status").then((r) => setStatus(r.data));
    api.get(`/ai/invocations/${sid}`).then((r) => setRows(r.data)).catch((e) => setErr(apiError(e)));
  }, [sid]);

  return (
    <Layout title="AI Activity">
      <div className="card">
        <div className="spread">
          <h3>Groq Integration</h3>
          {status && (
            <Badge value={status.configured ? "connected" : "no API key"} color={status.configured ? "green" : "amber"} />
          )}
        </div>
        <p className="muted">
          Every AI assist invoked by any stakeholder is logged here for transparency and audit.
        </p>
      </div>
      {err && <div className="error">{err}</div>}
      <div className="card">
        <h3>Invocations ({rows.length})</h3>
        {rows.length === 0 && <Empty>No AI calls yet.</Empty>}
        {rows.length > 0 && (
          <table>
            <thead><tr><th>When</th><th>Stage</th><th>Task</th><th>Model</th><th>Tokens</th><th></th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="muted">{new Date(r.created_at).toLocaleString()}</td>
                  <td>{r.stage_key}</td>
                  <td><Badge value={r.task} color="purple" /></td>
                  <td className="muted">{r.model}</td>
                  <td>{r.tokens}</td>
                  <td><button className="ghost btn-sm" onClick={() => setOpen(open === r.id ? null : r.id)}>{open === r.id ? "Hide" : "View"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {open && (
          <div className="ai-output" style={{ marginTop: 12 }}>
            {(() => {
              const r = rows.find((x) => x.id === open);
              return `PROMPT:\n${r.prompt}\n\nRESPONSE:\n${r.response}`;
            })()}
          </div>
        )}
      </div>
    </Layout>
  );
}

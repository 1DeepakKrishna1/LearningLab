import { useEffect, useState } from "react";
import Layout from "../../components/Layout.jsx";
import { Badge, Stat, Empty } from "../../components/ui.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import api, { apiError } from "../../api/client.js";

export default function Reports() {
  const { user } = useAuth();
  const sid = user.system_id;
  const [summary, setSummary] = useState(null);
  const [audit, setAudit] = useState([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!sid) return;
    Promise.all([
      api.get(`/systems/${sid}/reports/summary`),
      api.get(`/systems/${sid}/reports/audit`),
    ])
      .then(([s, a]) => { setSummary(s.data); setAudit(a.data); })
      .catch((e) => setErr(apiError(e)));
  }, [sid]);

  if (err) return <Layout title="Reports & Audit"><div className="error">{err}</div></Layout>;
  if (!summary) return <Layout title="Reports & Audit"><div className="loading">Loading…</div></Layout>;

  return (
    <Layout title="Reports & Audit">
      <div className="grid cols-3">
        <Stat num={summary.total_applications} label="Total Applications" />
        <Stat num={`${summary.fill_rate}%`} label="Seat Fill Rate" />
        <Stat num={summary.options.reduce((a, o) => a + o.filled, 0)} label="Allotted" />
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Applications by Status</h3>
          <table>
            <tbody>
              {Object.entries(summary.by_status).map(([k, v]) => (
                <tr key={k}><td><Badge value={k} /></td><td style={{ textAlign: "right" }}>{v}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Option Fill</h3>
          <table>
            <thead><tr><th>Option</th><th>Filled / Cap</th></tr></thead>
            <tbody>
              {summary.options.map((o) => (
                <tr key={o.key}><td>{o.label}</td><td>{o.filled} / {o.capacity}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>Audit Trail (latest 200)</h3>
        {audit.length === 0 && <Empty>No audit events yet.</Empty>}
        {audit.length > 0 && (
          <table>
            <thead><tr><th>When</th><th>Action</th><th>Entity</th><th>Detail</th></tr></thead>
            <tbody>
              {audit.map((a) => (
                <tr key={a.id}>
                  <td className="muted">{new Date(a.created_at).toLocaleString()}</td>
                  <td><Badge value={a.action} color="blue" /></td>
                  <td>{a.entity_type}{a.entity_id ? ` #${a.entity_id}` : ""}</td>
                  <td className="muted" style={{ fontSize: 12 }}>
                    {Object.keys(a.detail || {}).length ? JSON.stringify(a.detail) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}

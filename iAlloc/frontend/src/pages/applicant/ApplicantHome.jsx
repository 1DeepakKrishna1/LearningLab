import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../../components/Layout.jsx";
import { Badge, Empty } from "../../components/ui.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import api, { apiError } from "../../api/client.js";

export default function ApplicantHome() {
  const { user } = useAuth();
  const [apps, setApps] = useState([]);
  const [system, setSystem] = useState(null);
  const [form, setForm] = useState({});
  const [err, setErr] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    const [a, s] = await Promise.all([
      api.get("/applications/mine"),
      api.get(`/systems/${user.system_id}`),
    ]);
    setApps(a.data);
    setSystem(s.data);
  }
  useEffect(() => { if (user.system_id) load().catch((e) => setErr(apiError(e))); }, [user.system_id]);

  const fields = system?.config?.form_fields || [];
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function create(e) {
    e.preventDefault();
    setErr(""); setCreating(true);
    try {
      await api.post("/applications", { data: form });
      setForm({});
      load();
    } catch (e2) { setErr(apiError(e2)); }
    finally { setCreating(false); }
  }

  return (
    <Layout title="My Applications">
      {system && (
        <div className="card">
          <h3>{system.name}</h3>
          <p className="muted">{system.description}</p>
        </div>
      )}

      <div className="card">
        <h3>Start a New Application</h3>
        <form onSubmit={create}>
          <div className="grid cols-2">
            {fields.map((f) => (
              <div key={f.key}>
                <label>{f.label}{f.required && " *"}</label>
                {f.type === "select" ? (
                  <select value={form[f.key] || ""} onChange={set(f.key)} required={f.required}>
                    <option value="">Select…</option>
                    {(f.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input
                    type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                    value={form[f.key] || ""}
                    onChange={(e) => setForm({ ...form, [f.key]: f.type === "number" ? Number(e.target.value) : e.target.value })}
                    required={f.required}
                  />
                )}
              </div>
            ))}
          </div>
          <button style={{ marginTop: 16 }} disabled={creating}>
            {creating ? "Submitting…" : "Submit Application"}
          </button>
        </form>
        {err && <div className="error">{err}</div>}
      </div>

      <div className="card">
        <h3>Applications ({apps.length})</h3>
        {apps.length === 0 && <Empty>No applications yet.</Empty>}
        {apps.length > 0 && (
          <table>
            <thead><tr><th>Reference</th><th>Status</th><th>Stage</th><th>Score</th><th>Rank</th><th></th></tr></thead>
            <tbody>
              {apps.map((a) => (
                <tr key={a.id}>
                  <td>{a.reference_no}</td>
                  <td><Badge value={a.status} /></td>
                  <td>{a.current_stage_key || "—"}</td>
                  <td>{a.score ?? "—"}</td>
                  <td>{a.rank ?? "—"}</td>
                  <td><Link to={`/apply/${a.id}`}>Open →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Layout from "../../components/Layout.jsx";
import StageConfigEditor from "../../components/StageConfigEditor.jsx";
import { Badge } from "../../components/ui.jsx";
import api, { apiError } from "../../api/client.js";

export default function SystemDetail() {
  const { id } = useParams();
  const [system, setSystem] = useState(null);
  const [members, setMembers] = useState([]);
  const [err, setErr] = useState("");

  async function load() {
    const [s, m] = await Promise.all([
      api.get(`/admin/systems/${id}`),
      api.get(`/admin/systems/${id}/members`),
    ]);
    setSystem(s.data);
    setMembers(m.data);
  }
  useEffect(() => { load().catch((e) => setErr(apiError(e))); }, [id]);

  async function setStatus(status) {
    const { data } = await api.patch(`/admin/systems/${id}`, { status });
    setSystem(data);
  }

  if (err) return <Layout title="System"><div className="error">{err}</div></Layout>;
  if (!system) return <Layout title="System"><div className="loading">Loading…</div></Layout>;

  return (
    <Layout title={system.name}>
      <div className="card">
        <div className="spread">
          <div>
            <Badge value={system.domain} color="purple" /> &nbsp;
            <Badge value={system.status} />
            <p className="muted" style={{ marginBottom: 0 }}>{system.description}</p>
          </div>
          <div className="row">
            {system.status !== "active" && (
              <button className="btn-sm" onClick={() => setStatus("active")}>Activate</button>
            )}
            {system.status !== "closed" && (
              <button className="btn-sm secondary" onClick={() => setStatus("closed")}>Close</button>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Stakeholders ({members.length})</h3>
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Active</th></tr></thead>
          <tbody>
            {members.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td><Badge value={u.role} color="blue" /></td>
                <td>{u.is_active ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 style={{ marginTop: 24 }}>Lifecycle Configuration</h3>
      <p className="muted">Toggle stages and AI assistance. Changes persist to the system's JSON config.</p>
      <StageConfigEditor systemId={Number(id)} />
    </Layout>
  );
}

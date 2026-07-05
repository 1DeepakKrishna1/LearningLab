import { useEffect, useState } from "react";
import Layout from "../../components/Layout.jsx";
import { Badge } from "../../components/ui.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import api, { apiError } from "../../api/client.js";

const ROLES = [
  "verifier", "evaluator", "allocation_authority", "payment_agency",
  "auditor", "support", "institution", "reporting_authority", "system_admin",
];

export default function Members() {
  const { user } = useAuth();
  const sid = user.system_id;
  const [members, setMembers] = useState([]);
  const [form, setForm] = useState({ full_name: "", email: "", password: "Admin@123", role: "verifier" });
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    const { data } = await api.get(`/systems/${sid}/admin/members`);
    setMembers(data);
  }
  useEffect(() => { if (sid) load().catch((e) => setErr(apiError(e))); }, [sid]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function add(e) {
    e.preventDefault();
    setErr(""); setMsg("");
    try {
      await api.post(`/systems/${sid}/admin/members`, { ...form, system_id: sid });
      setMsg(`Created ${form.email}`);
      setForm({ ...form, full_name: "", email: "" });
      load();
    } catch (e2) {
      setErr(apiError(e2));
    }
  }

  async function toggleActive(m) {
    await api.patch(`/systems/${sid}/admin/members/${m.id}/active?active=${!m.is_active}`);
    load();
  }

  return (
    <Layout title="Stakeholders">
      <div className="grid cols-2">
        <div className="card">
          <h3>Add Stakeholder</h3>
          <form onSubmit={add}>
            <label>Full Name</label>
            <input value={form.full_name} onChange={set("full_name")} required />
            <label>Email</label>
            <input type="email" value={form.email} onChange={set("email")} required />
            <label>Role</label>
            <select value={form.role} onChange={set("role")}>
              {ROLES.map((r) => <option key={r} value={r}>{r.replace(/_/g, " ")}</option>)}
            </select>
            <label>Temporary Password</label>
            <input value={form.password} onChange={set("password")} />
            <button style={{ marginTop: 14 }}>Create stakeholder</button>
          </form>
          {err && <div className="error">{err}</div>}
          {msg && <div className="success">{msg}</div>}
        </div>

        <div className="card">
          <h3>Team ({members.length})</h3>
          <table>
            <thead><tr><th>Name</th><th>Role</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id}>
                  <td>{m.full_name}<br /><span className="muted">{m.email}</span></td>
                  <td><Badge value={m.role} color="blue" /></td>
                  <td><Badge value={m.is_active ? "active" : "disabled"} color={m.is_active ? "green" : "gray"} /></td>
                  <td>
                    <button className="ghost btn-sm" onClick={() => toggleActive(m)}>
                      {m.is_active ? "Disable" : "Enable"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}

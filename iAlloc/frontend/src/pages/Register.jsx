import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import api, { apiError } from "../api/client.js";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [systems, setSystems] = useState([]);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", system_id: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/systems/public").then((r) => {
      setSystems(r.data);
      if (r.data[0]) setForm((f) => ({ ...f, system_id: r.data[0].id }));
    });
  }, []);

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await register({ ...form, system_id: Number(form.system_id), role: "applicant" });
      nav("/");
    } catch (e2) {
      setErr(apiError(e2));
    } finally {
      setBusy(false);
    }
  }

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <h1>Join i<span>Alloc</span></h1>
        <div className="sub">Register as an applicant</div>
        <form onSubmit={submit}>
          <label>System / Programme</label>
          <select value={form.system_id} onChange={set("system_id")} required>
            {systems.length === 0 && <option value="">No active systems</option>}
            {systems.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <label>Full Name</label>
          <input value={form.full_name} onChange={set("full_name")} required />
          <label>Email</label>
          <input type="email" value={form.email} onChange={set("email")} required />
          <label>Password</label>
          <input type="password" value={form.password} onChange={set("password")} minLength={6} required />
          <button disabled={busy || systems.length === 0}>{busy ? "Creating…" : "Create account"}</button>
        </form>
        {err && <div className="error">{err}</div>}
        <div style={{ marginTop: 14, fontSize: 13 }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
}

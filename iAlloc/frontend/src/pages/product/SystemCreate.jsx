import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../../components/Layout.jsx";
import api, { apiError } from "../../api/client.js";

export default function SystemCreate() {
  const nav = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState({
    key: "", name: "", domain: "examination", description: "",
    system_admin_email: "", system_admin_name: "", system_admin_password: "Admin@123",
  });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/admin/domain-templates").then((r) => setTemplates(r.data));
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  function onDomain(e) {
    const domain = e.target.value;
    const t = templates.find((x) => x.domain === domain);
    setForm((f) => ({
      ...f, domain,
      name: f.name || (t ? t.name_suggestion : ""),
    }));
  }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const { data } = await api.post("/admin/systems", form);
      nav(`/product/systems/${data.id}`);
    } catch (e2) {
      setErr(apiError(e2));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Layout title="Create System">
      <div className="card" style={{ maxWidth: 640 }}>
        <p className="muted">
          A System is a JSON-configured instance of the 14-stage lifecycle. Pick a
          domain template to pre-fill stages, AI tasks, form fields and allocation
          options — all editable afterward by the SystemAdmin.
        </p>
        <form onSubmit={submit}>
          <label>Domain Template</label>
          <select value={form.domain} onChange={onDomain}>
            {templates.map((t) => (
              <option key={t.domain} value={t.domain}>
                {t.domain.replace(/_/g, " ")} — {t.name_suggestion}
              </option>
            ))}
          </select>

          <label>System Name</label>
          <input value={form.name} onChange={set("name")} required />

          <label>Unique Key (lowercase, a-z 0-9 _ -)</label>
          <input value={form.key} onChange={set("key")} pattern="[a-z0-9_\-]+" required placeholder="e.g. neet_ug_2026" />

          <label>Description</label>
          <textarea value={form.description} onChange={set("description")} />

          <h3 style={{ marginTop: 20 }}>Provision a System Admin</h3>
          <div className="grid cols-2">
            <div>
              <label>Admin Name</label>
              <input value={form.system_admin_name} onChange={set("system_admin_name")} />
            </div>
            <div>
              <label>Admin Email</label>
              <input type="email" value={form.system_admin_email} onChange={set("system_admin_email")} />
            </div>
          </div>
          <label>Temporary Password</label>
          <input value={form.system_admin_password} onChange={set("system_admin_password")} />

          <button disabled={busy} style={{ marginTop: 16 }}>
            {busy ? "Creating…" : "Create System"}
          </button>
        </form>
        {err && <div className="error">{err}</div>}
      </div>
    </Layout>
  );
}

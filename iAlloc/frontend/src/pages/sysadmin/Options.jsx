import { useEffect, useState } from "react";
import Layout from "../../components/Layout.jsx";
import { Empty } from "../../components/ui.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import api, { apiError } from "../../api/client.js";

export default function Options() {
  const { user } = useAuth();
  const sid = user.system_id;
  const [options, setOptions] = useState([]);
  const [form, setForm] = useState({ key: "", label: "", capacity: 1 });
  const [err, setErr] = useState("");

  async function load() {
    const { data } = await api.get(`/systems/${sid}/admin/options`);
    setOptions(data);
  }
  useEffect(() => { if (sid) load().catch((e) => setErr(apiError(e))); }, [sid]);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function add(e) {
    e.preventDefault();
    setErr("");
    try {
      await api.post(`/systems/${sid}/admin/options`, {
        ...form, capacity: Number(form.capacity), meta: {},
      });
      setForm({ key: "", label: "", capacity: 1 });
      load();
    } catch (e2) { setErr(apiError(e2)); }
  }

  async function remove(id) {
    await api.delete(`/systems/${sid}/admin/options/${id}`);
    load();
  }

  return (
    <Layout title="Allocation Options">
      <p className="muted">
        The finite resources the allocation engine distributes — seats, funds, rooms,
        jobs or contracts depending on the domain.
      </p>
      <div className="grid cols-2">
        <div className="card">
          <h3>Add Option</h3>
          <form onSubmit={add}>
            <label>Key</label>
            <input value={form.key} onChange={set("key")} required placeholder="e.g. iit_b_cse" />
            <label>Label</label>
            <input value={form.label} onChange={set("label")} required placeholder="e.g. IIT Bombay - CSE" />
            <label>Capacity</label>
            <input type="number" min="0" value={form.capacity} onChange={set("capacity")} />
            <button style={{ marginTop: 14 }}>Add option</button>
          </form>
          {err && <div className="error">{err}</div>}
        </div>
        <div className="card">
          <h3>Options ({options.length})</h3>
          {options.length === 0 && <Empty>No options configured.</Empty>}
          {options.length > 0 && (
            <table>
              <thead><tr><th>Label</th><th>Filled / Capacity</th><th></th></tr></thead>
              <tbody>
                {options.map((o) => (
                  <tr key={o.id}>
                    <td>{o.label}<br /><span className="muted">{o.key}</span></td>
                    <td>{o.filled} / {o.capacity}</td>
                    <td><button className="danger btn-sm" onClick={() => remove(o.id)}>Delete</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </Layout>
  );
}

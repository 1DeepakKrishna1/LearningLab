import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Layout from "../../components/Layout.jsx";
import AIAssist from "../../components/AIAssist.jsx";
import { Badge, Stepper, Empty } from "../../components/ui.jsx";
import api, { apiError } from "../../api/client.js";

export default function ApplicationDetail() {
  const { appId } = useParams();
  const [app, setApp] = useState(null);
  const [docs, setDocs] = useState([]);
  const [options, setOptions] = useState([]);
  const [prefs, setPrefs] = useState([]);
  const [payments, setPayments] = useState([]);
  const [allocation, setAllocation] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const [docForm, setDocForm] = useState({ name: "", doc_type: "marksheet", content_text: "" });
  const [selPrefs, setSelPrefs] = useState(null);

  async function load() {
    const a = await api.get(`/applications/${appId}`);
    setApp(a.data);
    const [d, p, pay, al] = await Promise.all([
      api.get(`/applications/${appId}/documents`),
      api.get(`/applications/${appId}/preferences`),
      api.get(`/applications/${appId}/payments`),
      api.get(`/applications/${appId}/allocation`),
    ]);
    setDocs(d.data); setPrefs(p.data); setPayments(pay.data); setAllocation(al.data);
    api.get(`/systems/${a.data.system_id}/options`).then((r) => setOptions(r.data)).catch(() => {});
  }
  useEffect(() => { load().catch((e) => setErr(apiError(e))); }, [appId]);

  if (err) return <Layout title="Application"><div className="error">{err}</div></Layout>;
  if (!app) return <Layout title="Application"><div className="loading">Loading…</div></Layout>;

  const sid = app.system_id;
  const stageTypes = new Set(app.progress.map((s) => s.type));
  const stage = (type) => app.progress.find((s) => s.type === type);

  async function uploadDoc(e) {
    e.preventDefault();
    await api.post(`/applications/${appId}/documents`, docForm);
    setDocForm({ name: "", doc_type: "marksheet", content_text: "" });
    load();
  }

  async function savePrefs(list) {
    await api.put(`/applications/${appId}/preferences`, {
      preferences: list.map((o, i) => ({ option_key: o.key, option_label: o.label, priority: i + 1 })),
    });
    setMsg("Preferences saved"); load();
  }

  async function pay() {
    await api.post(`/applications/${appId}/payments`, { amount: 1000, purpose: "application_fee" });
    load();
  }

  async function respond(decision) {
    await api.post(`/applications/${appId}/allocation/respond`, { decision });
    load();
  }

  const currentPrefKeys = (selPrefs ?? prefs.map((p) => ({ key: p.option_key, label: p.option_label })));

  return (
    <Layout title={`Application ${app.reference_no}`}>
      <div className="card">
        <div className="spread">
          <div><Badge value={app.status} /> &nbsp; Rank: <strong>{app.rank ?? "—"}</strong> &nbsp; Score: <strong>{app.score ?? "—"}</strong></div>
        </div>
        <div style={{ marginTop: 14 }}><Stepper stages={app.progress} /></div>
        <p className="muted" style={{ marginTop: 8, fontSize: 12 }}>
          ● purple dot = AI assistance available on that stage
        </p>
      </div>

      {msg && <div className="success">{msg}</div>}

      {/* Documents */}
      {stageTypes.has("document") && (
        <div className="card">
          <h3>Documents</h3>
          <form onSubmit={uploadDoc} className="grid cols-3" style={{ alignItems: "flex-end" }}>
            <div>
              <label>Name</label>
              <input value={docForm.name} onChange={(e) => setDocForm({ ...docForm, name: e.target.value })} required />
            </div>
            <div>
              <label>Type</label>
              <select value={docForm.doc_type} onChange={(e) => setDocForm({ ...docForm, doc_type: e.target.value })}>
                {["id_proof", "marksheet", "certificate", "photo", "signature", "other"].map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div><button>Upload</button></div>
            <div style={{ gridColumn: "1 / -1" }}>
              <label>Content / details (typed — used by AI completeness checks)</label>
              <textarea value={docForm.content_text} onChange={(e) => setDocForm({ ...docForm, content_text: e.target.value })} />
            </div>
          </form>
          <table style={{ marginTop: 12 }}>
            <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Remarks</th></tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}><td>{d.name}</td><td>{d.doc_type}</td><td><Badge value={d.status} /></td><td className="muted">{d.remarks || "—"}</td></tr>
              ))}
            </tbody>
          </table>
          {stage("document") && <AIAssist systemId={sid} stage={stage("document")} applicationId={app.id} placeholder="e.g. Are all mandatory documents present?" />}
        </div>
      )}

      {/* Preferences */}
      {stageTypes.has("preference") && (
        <div className="card">
          <h3>Preferences</h3>
          <p className="muted">Tick the options you want, in priority order of selection.</p>
          {options.length === 0 && <Empty>No options published yet.</Empty>}
          {options.map((o) => {
            const idx = currentPrefKeys.findIndex((p) => p.key === o.key);
            return (
              <label key={o.key} style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 400 }}>
                <input
                  type="checkbox"
                  style={{ width: "auto" }}
                  checked={idx >= 0}
                  onChange={(e) => {
                    const cur = [...currentPrefKeys];
                    if (e.target.checked) cur.push({ key: o.key, label: o.label });
                    else cur.splice(idx, 1);
                    setSelPrefs(cur);
                  }}
                />
                {idx >= 0 && <Badge value={`#${idx + 1}`} color="blue" />}
                {o.label} <span className="muted">({o.filled}/{o.capacity})</span>
              </label>
            );
          })}
          {options.length > 0 && (
            <button style={{ marginTop: 12 }} onClick={() => savePrefs(currentPrefKeys)}>Save Preferences</button>
          )}
          {stage("preference") && <AIAssist systemId={sid} stage={stage("preference")} applicationId={app.id} placeholder="Recommend a preference order given my rank." />}
        </div>
      )}

      {/* Payment */}
      {stageTypes.has("payment") && (
        <div className="card">
          <h3>Payments</h3>
          {payments.length === 0 ? (
            <p className="muted">No payments recorded.</p>
          ) : (
            <table>
              <thead><tr><th>Reference</th><th>Purpose</th><th>Amount</th><th>Status</th></tr></thead>
              <tbody>
                {payments.map((p) => (
                  <tr key={p.id}><td>{p.reference}</td><td>{p.purpose}</td><td>{p.currency} {p.amount}</td><td><Badge value={p.status} /></td></tr>
                ))}
              </tbody>
            </table>
          )}
          <button style={{ marginTop: 12 }} onClick={pay}>Pay Application Fee (₹1000)</button>
        </div>
      )}

      {/* Allocation */}
      {stageTypes.has("allocation") && (
        <div className="card">
          <h3>Allocation Result</h3>
          {allocation.length === 0 ? (
            <Empty>No allocation yet. Check back after counselling.</Empty>
          ) : (
            allocation.map((al) => (
              <div key={al.id} className="spread" style={{ marginBottom: 10 }}>
                <div>Allotted: <strong>{al.option_label}</strong> (round {al.round}) <Badge value={al.status} /></div>
                {al.status === "allotted" && (
                  <div className="row">
                    <button className="btn-sm" onClick={() => respond("accepted")}>Accept</button>
                    <button className="btn-sm secondary" onClick={() => respond("declined")}>Decline</button>
                  </div>
                )}
              </div>
            ))
          )}
          {stage("allocation") && <AIAssist systemId={sid} stage={stage("allocation")} applicationId={app.id} placeholder="Explain my allocation result." />}
        </div>
      )}

      {/* Any other AI-enabled stages (registration, eligibility, enrollment...) */}
      <div className="card">
        <h3>Stage Assistance</h3>
        {app.progress.filter((s) => s.ai_enabled && !["document", "preference", "allocation"].includes(s.type)).length === 0 && (
          <Empty>No additional AI-enabled stages.</Empty>
        )}
        {app.progress
          .filter((s) => s.ai_enabled && !["document", "preference", "allocation"].includes(s.type))
          .map((s) => <AIAssist key={s.key} systemId={sid} stage={s} applicationId={app.id} />)}
      </div>
    </Layout>
  );
}

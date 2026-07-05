import { useEffect, useState } from "react";
import Layout from "../../components/Layout.jsx";
import AIAssist from "../../components/AIAssist.jsx";
import { Badge, Empty, Stat } from "../../components/ui.jsx";
import { useAuth } from "../../auth/AuthContext.jsx";
import api, { apiError } from "../../api/client.js";

export default function StaffHome() {
  const { user } = useAuth();
  const sid = user.system_id;
  const role = user.role;
  const [apps, setApps] = useState([]);
  const [stages, setStages] = useState([]);
  const [pendingDocs, setPendingDocs] = useState([]);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [scoreForm, setScoreForm] = useState({});

  const stageByType = (t) => stages.find((s) => s.type === t);

  async function load() {
    const [a, s] = await Promise.all([
      api.get(`/systems/${sid}/staff/applications`),
      api.get(`/systems/${sid}/stages`),
    ]);
    setApps(a.data);
    setStages(s.data);
    if (role === "verifier") {
      const d = await api.get(`/systems/${sid}/staff/documents/pending`);
      setPendingDocs(d.data);
    }
  }
  useEffect(() => { if (sid) load().catch((e) => setErr(apiError(e))); }, [sid]);

  async function verifyDoc(docId, status) {
    await api.patch(`/systems/${sid}/staff/documents/${docId}/verify`, { status, remarks: "" });
    load();
  }
  async function setEligibility(appId, eligible) {
    await api.post(`/systems/${sid}/staff/applications/${appId}/eligibility?eligible=${eligible}`);
    setMsg(`Eligibility ${eligible ? "approved" : "rejected"} for #${appId}`);
    load();
  }
  async function submitScore(appId) {
    const f = scoreForm[appId] || {};
    await api.post(`/systems/${sid}/staff/evaluations`, {
      application_id: appId, stage_key: "evaluation",
      score: Number(f.score || 0), max_score: Number(f.max || 100),
      criteria: {}, remarks: f.remarks || "",
    });
    setMsg(`Score recorded for #${appId}`);
    load();
  }
  async function generateRanking() {
    await api.post(`/systems/${sid}/staff/ranking/generate`);
    setMsg("Merit ranking generated"); load();
  }
  async function runAllocation() {
    const { data } = await api.post(`/systems/${sid}/staff/allocation/run?round_no=1`);
    setMsg(`Allocation done — ${data.allotted} allotted, ${data.waitlisted} waitlisted`);
    load();
  }

  if (!sid) return <Layout title="Workspace"><Empty>Not bound to a system.</Empty></Layout>;

  const title = {
    verifier: "Verification Queue", evaluator: "Evaluation Queue",
    allocation_authority: "Ranking & Allocation", reporting_authority: "Merit List",
    auditor: "Applications (read-only)",
  }[role] || "Workspace";

  return (
    <Layout title={title}>
      {err && <div className="error">{err}</div>}
      {msg && <div className="success">{msg}</div>}

      <div className="grid cols-3">
        <Stat num={apps.length} label="Applications" />
        <Stat num={apps.filter((a) => a.rank).length} label="Ranked" />
        <Stat num={apps.filter((a) => a.status === "allocated" || a.status === "enrolled").length} label="Allocated" />
      </div>

      {/* Verifier */}
      {role === "verifier" && (
        <>
          <div className="card">
            <h3>Pending Documents ({pendingDocs.length})</h3>
            {pendingDocs.length === 0 && <Empty>Nothing to verify.</Empty>}
            {pendingDocs.length > 0 && (
              <table>
                <thead><tr><th>Name</th><th>Type</th><th>Content</th><th>Action</th></tr></thead>
                <tbody>
                  {pendingDocs.map((d) => (
                    <tr key={d.id}>
                      <td>{d.name}</td><td>{d.doc_type}</td>
                      <td className="muted" style={{ maxWidth: 280 }}>{(d.content_text || "").slice(0, 120) || "—"}</td>
                      <td className="row">
                        <button className="btn-sm" onClick={() => verifyDoc(d.id, "verified")}>Verify</button>
                        <button className="btn-sm danger" onClick={() => verifyDoc(d.id, "rejected")}>Reject</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {stageByType("document") && <AIAssist systemId={sid} stage={stageByType("document")} />}
          </div>

          <div className="card">
            <h3>Eligibility Decisions</h3>
            <table>
              <thead><tr><th>Ref</th><th>Applicant data</th><th>Status</th><th>Decision</th></tr></thead>
              <tbody>
                {apps.map((a) => (
                  <tr key={a.id}>
                    <td>{a.reference_no}</td>
                    <td className="muted" style={{ fontSize: 12 }}>{JSON.stringify(a.data)}</td>
                    <td><Badge value={a.status} /></td>
                    <td className="row">
                      <button className="btn-sm" onClick={() => setEligibility(a.id, true)}>Eligible</button>
                      <button className="btn-sm danger" onClick={() => setEligibility(a.id, false)}>Ineligible</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {stageByType("eligibility") && <AIAssist systemId={sid} stage={stageByType("eligibility")} />}
          </div>
        </>
      )}

      {/* Evaluator */}
      {role === "evaluator" && (
        <div className="card">
          <h3>Score Applications</h3>
          <table>
            <thead><tr><th>Ref</th><th>Data</th><th>Score</th><th>Max</th><th>Remarks</th><th></th></tr></thead>
            <tbody>
              {apps.map((a) => {
                const f = scoreForm[a.id] || {};
                const upd = (k, v) => setScoreForm({ ...scoreForm, [a.id]: { ...f, [k]: v } });
                return (
                  <tr key={a.id}>
                    <td>{a.reference_no}</td>
                    <td className="muted" style={{ fontSize: 12, maxWidth: 200 }}>{JSON.stringify(a.data)}</td>
                    <td><input style={{ width: 70 }} type="number" value={f.score || ""} onChange={(e) => upd("score", e.target.value)} /></td>
                    <td><input style={{ width: 70 }} type="number" value={f.max || 100} onChange={(e) => upd("max", e.target.value)} /></td>
                    <td><input value={f.remarks || ""} onChange={(e) => upd("remarks", e.target.value)} /></td>
                    <td><button className="btn-sm" onClick={() => submitScore(a.id)}>Save</button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {stageByType("evaluation") && <AIAssist systemId={sid} stage={stageByType("evaluation")} placeholder="Score this response against the rubric…" />}
        </div>
      )}

      {/* Allocation authority */}
      {role === "allocation_authority" && (
        <div className="card">
          <h3>Counselling & Allocation</h3>
          <div className="row" style={{ marginBottom: 14 }}>
            <button onClick={generateRanking}>1 · Generate Merit Ranking</button>
            <button className="secondary" onClick={runAllocation}>2 · Run Allocation Engine</button>
          </div>
          {(stageByType("ranking") || stageByType("allocation")) &&
            <AIAssist systemId={sid} stage={stageByType("allocation") || stageByType("ranking")} placeholder="Recommend / explain the allocation given ranks, preferences and capacities." />}
        </div>
      )}

      {/* Merit list (everyone in staff sees it) */}
      <div className="card">
        <h3>Merit List</h3>
        {apps.filter((a) => a.rank).length === 0 ? (
          <Empty>No ranking generated yet.</Empty>
        ) : (
          <table>
            <thead><tr><th>Rank</th><th>Ref</th><th>Score</th><th>Status</th></tr></thead>
            <tbody>
              {apps.filter((a) => a.rank).sort((a, b) => a.rank - b.rank).map((a) => (
                <tr key={a.id}><td><strong>{a.rank}</strong></td><td>{a.reference_no}</td><td>{a.score}</td><td><Badge value={a.status} /></td></tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}

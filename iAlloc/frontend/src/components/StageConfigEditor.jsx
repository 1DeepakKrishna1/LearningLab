import { useEffect, useState } from "react";
import api, { apiError } from "../api/client.js";
import { Badge } from "./ui.jsx";

/**
 * Lets an admin enable/disable each stage, rename it, and toggle/configure AI.
 * Works against /api/systems/{id}/admin endpoints (ProductAdmin or SystemAdmin).
 */
export default function StageConfigEditor({ systemId }) {
  const [config, setConfig] = useState(null);
  const [catalog, setCatalog] = useState(null);
  const [err, setErr] = useState("");
  const [savingKey, setSavingKey] = useState("");

  async function load() {
    const [cfg, cat] = await Promise.all([
      api.get(`/systems/${systemId}/admin/config`),
      api.get(`/systems/${systemId}/admin/catalog`),
    ]);
    setConfig(cfg.data.config);
    setCatalog(cat.data);
  }
  useEffect(() => { load().catch((e) => setErr(apiError(e))); }, [systemId]);

  async function patchStage(stage, changes) {
    setSavingKey(stage.key);
    setErr("");
    try {
      const body = {};
      if ("enabled" in changes) body.enabled = changes.enabled;
      if ("name" in changes) body.name = changes.name;
      if ("ai" in changes) body.ai = changes.ai;
      const { data } = await api.patch(
        `/systems/${systemId}/admin/stages/${stage.key}`, body
      );
      setConfig(data.config);
    } catch (e) {
      setErr(apiError(e));
    } finally {
      setSavingKey("");
    }
  }

  if (err) return <div className="error">{err}</div>;
  if (!config) return <div className="loading">Loading configuration…</div>;

  const tasksForType = (type) => {
    const c = (catalog?.stage_catalog || []).find((s) => s.type === type);
    return c ? c.ai_tasks : [];
  };

  return (
    <div>
      {config.stages.sort((a, b) => a.order - b.order).map((s) => {
        const ai = s.ai || {};
        const tasks = tasksForType(s.type);
        return (
          <div className="card" key={s.key} style={{ opacity: s.enabled ? 1 : 0.6 }}>
            <div className="spread">
              <div>
                <strong>{s.order}. {s.name}</strong>{" "}
                <Badge value={s.type} color="gray" />
                {tasks.length === 0 && <span className="muted"> · no AI tasks</span>}
              </div>
              <label className="toggle" title="Stage enabled">
                <input
                  type="checkbox"
                  checked={s.enabled}
                  disabled={savingKey === s.key}
                  onChange={(e) => patchStage(s, { enabled: e.target.checked })}
                />
                <span className="slider" />
              </label>
            </div>

            {tasks.length > 0 && (
              <div className="row" style={{ marginTop: 12, alignItems: "flex-end" }}>
                <div>
                  <label style={{ marginTop: 0 }}>AI Assist</label>
                  <label className="toggle">
                    <input
                      type="checkbox"
                      checked={!!ai.enabled}
                      disabled={savingKey === s.key}
                      onChange={(e) =>
                        patchStage(s, {
                          ai: { ...ai, enabled: e.target.checked,
                                task: ai.task || tasks[0], instructions: ai.instructions || "" },
                        })
                      }
                    />
                    <span className="slider" />
                  </label>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <label style={{ marginTop: 0 }}>AI Task</label>
                  <select
                    value={ai.task || tasks[0]}
                    disabled={!ai.enabled || savingKey === s.key}
                    onChange={(e) =>
                      patchStage(s, { ai: { ...ai, enabled: true, task: e.target.value } })
                    }
                  >
                    {tasks.map((t) => (
                      <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            {ai.enabled && (
              <div style={{ marginTop: 8 }}>
                <label style={{ marginTop: 0 }}>Extra instructions for the AI (optional)</label>
                <textarea
                  defaultValue={ai.instructions || ""}
                  placeholder="e.g. Apply the 2026 eligibility rules; minimum 75% in Class 12."
                  onBlur={(e) =>
                    e.target.value !== (ai.instructions || "") &&
                    patchStage(s, { ai: { ...ai, instructions: e.target.value } })
                  }
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

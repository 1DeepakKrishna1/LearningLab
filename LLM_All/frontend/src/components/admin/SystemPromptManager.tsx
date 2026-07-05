import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { adminApi } from "../../api/client";
import { SystemConfig } from "../../types";

const LLM_OPTIONS = [
  { value: "openai", label: "OpenAI (GPT-4o)" },
  { value: "anthropic", label: "Anthropic (Claude)" },
  { value: "google", label: "Google (Gemini)" },
  { value: "groq", label: "Groq (Llama)" },
];

const MODEL_OPTIONS: Record<string, string[]> = {
  openai: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
  anthropic: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
  google: ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
  groq: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
};

export default function SystemPromptManager() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    adminApi.getSystemConfig().then(({ data }) => setConfig(data));
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setMessage("");
    try {
      const { data } = await adminApi.updateSystemConfig(config);
      setConfig(data);
      setMessage("System configuration saved.");
    } catch {
      setMessage("Failed to save configuration.");
    } finally {
      setSaving(false);
    }
  };

  if (!config) return <div className="text-gray-400 text-sm">Loading…</div>;

  const currentModels = MODEL_OPTIONS[config.active_llm] || [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">System Prompt & LLM Configuration</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Choose the active LLM and configure the system prompt for all conversations.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Active LLM Provider</label>
          <select
            value={config.active_llm}
            onChange={(e) =>
              setConfig((prev) => prev ? { ...prev, active_llm: e.target.value } : prev)
            }
            className="input-field"
          >
            {LLM_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
          <select
            value={config.models[config.active_llm] || ""}
            onChange={(e) =>
              setConfig((prev) =>
                prev
                  ? { ...prev, models: { ...prev.models, [prev.active_llm]: e.target.value } }
                  : prev
              )
            }
            className="input-field"
          >
            {currentModels.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Context Window (message pairs)</label>
        <input
          type="number"
          min={1}
          max={20}
          value={config.context_window}
          onChange={(e) =>
            setConfig((prev) => prev ? { ...prev, context_window: Number(e.target.value) } : prev)
          }
          className="input-field w-32"
        />
        <p className="text-xs text-gray-400 mt-1">
          Last N user/assistant exchanges to include as context. Older messages are summarised.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">System Prompt</label>
        <textarea
          value={config.system_prompt}
          onChange={(e) =>
            setConfig((prev) => prev ? { ...prev, system_prompt: e.target.value } : prev)
          }
          rows={8}
          className="input-field font-mono text-sm"
          placeholder="Enter the system prompt…"
        />
      </div>

      {message && (
        <p className={`text-sm ${message.includes("saved") ? "text-green-600" : "text-red-600"}`}>
          {message}
        </p>
      )}

      <button onClick={handleSave} className="btn-primary flex items-center gap-2" disabled={saving}>
        <Save className="w-4 h-4" />
        {saving ? "Saving…" : "Save Configuration"}
      </button>
    </div>
  );
}

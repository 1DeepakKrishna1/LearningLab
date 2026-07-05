import { Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { adminApi } from "../../api/client";
import { Guardrails, GuardrailRule } from "../../types";

const RULE_TYPES = [
  { value: "keyword_block", label: "Keyword Block (input)" },
  { value: "output_filter", label: "Output Filter (response)" },
  { value: "topic_restriction", label: "Topic Restriction" },
];

function RuleCard({
  rule,
  onChange,
  onDelete,
}: {
  rule: GuardrailRule;
  onChange: (r: GuardrailRule) => void;
  onDelete: () => void;
}) {
  const [kwInput, setKwInput] = useState("");

  const addKeyword = () => {
    const kw = kwInput.trim();
    if (kw && !rule.keywords.includes(kw)) {
      onChange({ ...rule, keywords: [...rule.keywords, kw] });
    }
    setKwInput("");
  };

  return (
    <div className="border border-gray-200 rounded-xl p-4 space-y-3 bg-white">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={rule.enabled}
            onChange={(e) => onChange({ ...rule, enabled: e.target.checked })}
            className="w-4 h-4 accent-indigo-600"
          />
          <input
            type="text"
            value={rule.name}
            onChange={(e) => onChange({ ...rule, name: e.target.value })}
            className="font-medium text-gray-900 border-b border-transparent hover:border-gray-300 focus:border-indigo-500 focus:outline-none bg-transparent"
          />
        </div>
        <button onClick={onDelete} className="text-gray-400 hover:text-red-500 transition-colors">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Type</label>
          <select
            value={rule.type}
            onChange={(e) => onChange({ ...rule, type: e.target.value })}
            className="input-field text-sm"
          >
            {RULE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
          <input
            type="text"
            value={rule.description}
            onChange={(e) => onChange({ ...rule, description: e.target.value })}
            className="input-field text-sm"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Blocked Keywords / Phrases</label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={kwInput}
            onChange={(e) => setKwInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
            placeholder="Add keyword and press Enter"
            className="input-field text-sm flex-1"
          />
          <button onClick={addKeyword} className="btn-secondary text-sm px-3 py-1.5">Add</button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {rule.keywords.map((kw, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 bg-gray-100 text-gray-700 px-2.5 py-0.5 rounded-full text-xs"
            >
              {kw}
              <button
                onClick={() => onChange({ ...rule, keywords: rule.keywords.filter((_, j) => j !== i) })}
                className="text-gray-400 hover:text-red-500"
              >
                ×
              </button>
            </span>
          ))}
          {rule.keywords.length === 0 && (
            <span className="text-xs text-gray-400 italic">No keywords yet</span>
          )}
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Blocked Response Message</label>
        <input
          type="text"
          value={rule.response}
          onChange={(e) => onChange({ ...rule, response: e.target.value })}
          className="input-field text-sm"
        />
      </div>
    </div>
  );
}

export default function GuardrailsManager() {
  const [guardrails, setGuardrails] = useState<Guardrails | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    adminApi.getGuardrails().then(({ data }) => setGuardrails(data));
  }, []);

  const addRule = () => {
    if (!guardrails) return;
    const newRule: GuardrailRule = {
      id: `rule_${Date.now()}`,
      name: "New Rule",
      description: "",
      enabled: true,
      type: "keyword_block",
      keywords: [],
      response: "This request cannot be processed.",
    };
    setGuardrails({ ...guardrails, rules: [...guardrails.rules, newRule] });
  };

  const updateRule = (index: number, updated: GuardrailRule) => {
    if (!guardrails) return;
    const rules = [...guardrails.rules];
    rules[index] = updated;
    setGuardrails({ ...guardrails, rules });
  };

  const deleteRule = (index: number) => {
    if (!guardrails) return;
    setGuardrails({ ...guardrails, rules: guardrails.rules.filter((_, i) => i !== index) });
  };

  const handleSave = async () => {
    if (!guardrails) return;
    setSaving(true);
    setMessage("");
    try {
      const { data } = await adminApi.updateGuardrails(guardrails);
      setGuardrails(data);
      setMessage("Guardrails saved successfully.");
    } catch {
      setMessage("Failed to save guardrails.");
    } finally {
      setSaving(false);
    }
  };

  if (!guardrails) return <div className="text-gray-400 text-sm">Loading…</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Guardrails Configuration</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Define rules to filter and moderate input/output content.
          </p>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <span className="text-sm font-medium text-gray-700">Guardrails enabled</span>
          <div
            onClick={() => setGuardrails({ ...guardrails, enabled: !guardrails.enabled })}
            className={`relative w-12 h-6 rounded-full transition-colors cursor-pointer ${
              guardrails.enabled ? "bg-indigo-600" : "bg-gray-300"
            }`}
          >
            <div
              className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                guardrails.enabled ? "translate-x-7" : "translate-x-1"
              }`}
            />
          </div>
        </label>
      </div>

      <div className="space-y-4">
        {guardrails.rules.map((rule, i) => (
          <RuleCard
            key={rule.id}
            rule={rule}
            onChange={(r) => updateRule(i, r)}
            onDelete={() => deleteRule(i)}
          />
        ))}
      </div>

      <button onClick={addRule} className="btn-secondary flex items-center gap-2 w-full justify-center">
        <Plus className="w-4 h-4" />
        Add Rule
      </button>

      {message && (
        <p className={`text-sm ${message.includes("success") ? "text-green-600" : "text-red-600"}`}>
          {message}
        </p>
      )}

      <button onClick={handleSave} className="btn-primary flex items-center gap-2" disabled={saving}>
        <Save className="w-4 h-4" />
        {saving ? "Saving…" : "Save Guardrails"}
      </button>
    </div>
  );
}

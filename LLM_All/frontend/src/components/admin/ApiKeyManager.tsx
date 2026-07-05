import { Eye, EyeOff, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { adminApi } from "../../api/client";

const PROVIDERS = [
  { key: "openai", label: "OpenAI (GPT-4o)", placeholder: "sk-..." },
  { key: "anthropic", label: "Anthropic (Claude)", placeholder: "sk-ant-..." },
  { key: "google", label: "Google (Gemini)", placeholder: "AIza..." },
  { key: "groq", label: "Groq (Llama / Mixtral)", placeholder: "gsk_..." },
];

export default function ApiKeyManager() {
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [show, setShow] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    adminApi.getApiKeys().then(({ data }) => setKeys(data));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    try {
      await adminApi.updateApiKeys(keys);
      setMessage("API keys saved successfully.");
    } catch {
      setMessage("Failed to save API keys.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">API Key Management</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Keys are stored securely in the server's .env file. Existing keys are masked.
        </p>
      </div>

      <div className="space-y-4">
        {PROVIDERS.map(({ key, label, placeholder }) => (
          <div key={key}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <div className="relative">
              <input
                type={show[key] ? "text" : "password"}
                value={keys[key] || ""}
                onChange={(e) => setKeys((prev) => ({ ...prev, [key]: e.target.value }))}
                placeholder={placeholder}
                className="input-field pr-10"
              />
              <button
                type="button"
                onClick={() => setShow((prev) => ({ ...prev, [key]: !prev[key] }))}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {show[key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
        ))}
      </div>

      {message && (
        <p className={`text-sm ${message.includes("success") ? "text-green-600" : "text-red-600"}`}>
          {message}
        </p>
      )}

      <button onClick={handleSave} className="btn-primary flex items-center gap-2" disabled={saving}>
        <Save className="w-4 h-4" />
        {saving ? "Saving…" : "Save API Keys"}
      </button>
    </div>
  );
}

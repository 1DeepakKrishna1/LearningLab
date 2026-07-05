import { Bot, Key, LogOut, MessageSquare, Settings, Shield } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ApiKeyManager from "../components/admin/ApiKeyManager";
import ConversationManager from "../components/admin/ConversationManager";
import GuardrailsManager from "../components/admin/GuardrailsManager";
import SystemPromptManager from "../components/admin/SystemPromptManager";
import { useAuth } from "../contexts/AuthContext";

type Tab = "api-keys" | "system-prompt" | "guardrails" | "conversations";

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: "api-keys", label: "API Keys", icon: <Key className="w-4 h-4" /> },
  { key: "system-prompt", label: "System Prompt", icon: <Settings className="w-4 h-4" /> },
  { key: "guardrails", label: "Guardrails", icon: <Shield className="w-4 h-4" /> },
  { key: "conversations", label: "Conversations", icon: <MessageSquare className="w-4 h-4" /> },
];

export default function Admin() {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("api-keys");

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-sm">AI Bot Admin</p>
              <p className="text-xs text-gray-500">{auth?.username}</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                tab === t.key
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-gray-200">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-3xl mx-auto">
          {tab === "api-keys" && <ApiKeyManager />}
          {tab === "system-prompt" && <SystemPromptManager />}
          {tab === "guardrails" && <GuardrailsManager />}
          {tab === "conversations" && <ConversationManager />}
        </div>
      </main>
    </div>
  );
}

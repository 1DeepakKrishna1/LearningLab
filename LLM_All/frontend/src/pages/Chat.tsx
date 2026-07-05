import { Bot, LogOut } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import ChatWindow from "../components/chat/ChatWindow";
import { useNavigate } from "react-router-dom";

export default function Chat() {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (!auth?.conversationId) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        No active conversation. Please log in again.
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">AI Conversational Bot</h1>
            <p className="text-xs text-gray-500">Conversation · {auth.conversationId.slice(0, 8)}…</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">Hello, <strong>{auth.username}</strong></span>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </header>

      {/* Chat area */}
      <main className="flex-1 flex flex-col overflow-hidden max-w-4xl w-full mx-auto">
        <ChatWindow conversationId={auth.conversationId} />
      </main>
    </div>
  );
}

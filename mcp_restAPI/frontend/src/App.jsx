import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import Chat from "./components/Chat.jsx";
import ApprovalModal from "./components/ApprovalModal.jsx";

const EMPTY_AUTH = {
  type: "none",
  api_key: "",
  api_key_name: "",
  api_key_location: "header",
  token: "",
  username: "",
  password: "",
};

export default function App() {
  const [health, setHealth] = useState(null);
  const [specs, setSpecs] = useState([]);
  const [activeSpec, setActiveSpec] = useState(null);
  const [auth, setAuth] = useState(EMPTY_AUTH);

  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [pendingApproval, setPendingApproval] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const refreshSpecs = async () => {
    const list = await api.listSpecs();
    setSpecs(list);
    return list;
  };

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "down" }));
    refreshSpecs().catch((e) => setError(e.message));
  }, []);

  // Switching the active spec starts a fresh conversation.
  const selectSpec = (spec) => {
    setActiveSpec(spec);
    setSessionId(null);
    setMessages([]);
    setPendingApproval(null);
    setError(null);
  };

  const applyResponse = (resp) => {
    setSessionId(resp.session_id);
    const assistant = {
      role: "assistant",
      content: resp.message,
      apiCalls: resp.api_calls || [],
    };
    setMessages((prev) => [...prev, assistant]);
    setPendingApproval(resp.status === "approval" ? resp.pending_approval : null);
  };

  const sendMessage = async (text) => {
    if (!activeSpec) {
      setError("Import and select an API spec first.");
      return;
    }
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setBusy(true);
    try {
      const resp = await api.chat({
        session_id: sessionId,
        spec_id: activeSpec.id,
        message: text,
        auth,
      });
      applyResponse(resp);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const decideApproval = async (approved, reason) => {
    if (!pendingApproval) return;
    setBusy(true);
    setError(null);
    const decisionNote = {
      role: "system-event",
      content: approved
        ? `✓ Approved ${pendingApproval.method} ${pendingApproval.url}`
        : `✕ Rejected ${pendingApproval.method} ${pendingApproval.url}`,
    };
    setMessages((prev) => [...prev, decisionNote]);
    setPendingApproval(null);
    try {
      const resp = await api.approve({
        session_id: sessionId,
        approval_id: pendingApproval.approval_id,
        approved,
        reason: reason || null,
      });
      applyResponse(resp);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        health={health}
        specs={specs}
        activeSpec={activeSpec}
        auth={auth}
        setAuth={setAuth}
        onSelect={selectSpec}
        onRefreshList={refreshSpecs}
        onError={setError}
      />
      <main className="main">
        <header className="topbar">
          <div>
            <h1>{activeSpec ? activeSpec.title : "RESTAPI AI Agent"}</h1>
            {activeSpec && (
              <p className="subtitle">
                {activeSpec.operation_count} operations · {activeSpec.base_url || "no base URL"}
              </p>
            )}
          </div>
          {health && (
            <span className={`badge ${health.llm_configured ? "ok" : "warn"}`}>
              {health.llm_configured ? `LLM: ${health.model}` : "LLM not configured"}
            </span>
          )}
        </header>

        {error && <div className="error-bar">{error}</div>}

        <Chat
          messages={messages}
          busy={busy}
          disabled={!activeSpec || !!pendingApproval}
          onSend={sendMessage}
          placeholder={
            activeSpec
              ? 'e.g. "Create a customer named John" or "List all orders"'
              : "Import and select an API spec to begin…"
          }
        />
      </main>

      {pendingApproval && (
        <ApprovalModal
          approval={pendingApproval}
          busy={busy}
          onApprove={() => decideApproval(true)}
          onReject={(reason) => decideApproval(false, reason)}
        />
      )}
    </div>
  );
}

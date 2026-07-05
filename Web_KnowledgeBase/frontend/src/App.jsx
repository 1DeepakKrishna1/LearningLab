import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client.js";
import IngestBar from "./components/IngestBar.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import SearchPanel from "./components/SearchPanel.jsx";
import NavigatePanel from "./components/NavigatePanel.jsx";
import ManagePanel from "./components/ManagePanel.jsx";

const TABS = ["Chat", "Search", "Navigate", "Manage"];

export default function App() {
  const [status, setStatus] = useState(null);
  const [tab, setTab] = useState("Chat");
  const [selectedPageId, setSelectedPageId] = useState(null);

  const refresh = useCallback(() => {
    api.status().then(setStatus).catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const ready = !!status?.ready;

  function openPage(pageId) {
    setSelectedPageId(pageId);
    setTab("Navigate");
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◆</span>
          <div>
            <div className="title">Knowledge Portal AI Agent</div>
            <div className="subtitle">
              {ready ? `${status.domain} · ${status.llm_model}` : "Crawl a portal, then search, chat & reason over it"}
            </div>
          </div>
        </div>
      </header>

      <IngestBar status={status} onReady={refresh} />

      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t} className={tab === t ? "tab active" : "tab"} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </nav>

      <main className="content">
        {tab === "Chat" && <ChatPanel ready={ready} />}
        {tab === "Search" && <SearchPanel ready={ready} onOpenPage={openPage} />}
        {tab === "Navigate" && (
          <NavigatePanel ready={ready} selectedPageId={selectedPageId} onSelect={setSelectedPageId} />
        )}
        {tab === "Manage" && <ManagePanel ready={ready} onChanged={refresh} />}
      </main>
    </div>
  );
}

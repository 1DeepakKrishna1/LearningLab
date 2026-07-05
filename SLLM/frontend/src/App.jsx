import { useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi! Ask me anything about your documents.", sources: [] },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "down" }));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);

    // Push the user message + an empty assistant message we'll stream into.
    setMessages((m) => [
      ...m,
      { role: "user", content: text },
      { role: "assistant", content: "", sources: [] },
    ]);

    try {
      const res = await fetch(`${API}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // The backend streams newline-delimited JSON events.
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep last partial line
        for (const line of lines) {
          if (!line.trim()) continue;
          const evt = JSON.parse(line);
          if (evt.type === "token") {
            setMessages((m) => patchLast(m, (last) => ({ ...last, content: last.content + evt.content })));
          } else if (evt.type === "sources") {
            setMessages((m) => patchLast(m, (last) => ({ ...last, sources: evt.sources })));
          } else if (evt.type === "error") {
            setMessages((m) => patchLast(m, (last) => ({ ...last, content: `⚠️ ${evt.content}` })));
          }
        }
      }
    } catch (err) {
      setMessages((m) => patchLast(m, (last) => ({ ...last, content: `⚠️ Could not reach the backend (${err.message}).` })));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>SLLM Chatbot</h1>
        <span className={`status ${health?.knowledge_base_ready ? "ok" : "warn"}`}>
          {health == null
            ? "connecting…"
            : health.status !== "ok"
            ? "backend down"
            : health.knowledge_base_ready
            ? `${health.chat_model} · KB ready`
            : `${health.chat_model} · KB empty (run the pipeline)`}
        </span>
      </header>

      <main ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">
              {m.content || <span className="cursor">▌</span>}
              {m.role === "assistant" && m.sources?.length > 0 && (
                <div className="sources">Sources: {m.sources.join(", ")}</div>
              )}
            </div>
          </div>
        ))}
      </main>

      <footer>
        <textarea
          value={input}
          placeholder="Ask a question…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button onClick={send} disabled={busy}>
          {busy ? "…" : "Send"}
        </button>
      </footer>
    </div>
  );
}

// Immutably replace the last message in the list.
function patchLast(messages, fn) {
  const copy = messages.slice();
  copy[copy.length - 1] = fn(copy[copy.length - 1]);
  return copy;
}

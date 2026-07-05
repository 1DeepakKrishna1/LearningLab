import { useRef, useState } from "react";
import { api, chatStream } from "../api/client.js";
import Sources from "./Sources.jsx";

export default function ChatPanel({ ready }) {
  const [messages, setMessages] = useState([]); // {role, content, sources?, steps?}
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [agentic, setAgentic] = useState(false);
  const scroller = useRef(null);

  function scrollDown() {
    requestAnimationFrame(() => {
      if (scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight;
    });
  }

  async function send(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    const next = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    scrollDown();

    try {
      if (agentic) {
        const res = await api.chat(text, history);
        setMessages((m) => [
          ...m,
          { role: "assistant", content: res.answer, sources: res.sources, steps: res.steps },
        ]);
      } else {
        // Insert a placeholder assistant message we fill as tokens stream in.
        let idx;
        setMessages((m) => {
          idx = m.length;
          return [...m, { role: "assistant", content: "", sources: [] }];
        });
        await chatStream(
          { message: text, history },
          {
            onToken: (t) =>
              setMessages((m) => {
                const copy = [...m];
                copy[copy.length - 1] = {
                  ...copy[copy.length - 1],
                  content: copy[copy.length - 1].content + t,
                };
                return copy;
              }),
            onSources: (s) =>
              setMessages((m) => {
                const copy = [...m];
                copy[copy.length - 1] = { ...copy[copy.length - 1], sources: s };
                return copy;
              }),
            onError: (err) =>
              setMessages((m) => {
                const copy = [...m];
                copy[copy.length - 1] = { ...copy[copy.length - 1], content: `⚠ ${err.message}` };
                return copy;
              }),
          }
        );
      }
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠ ${err.message}` }]);
    } finally {
      setBusy(false);
      scrollDown();
    }
  }

  return (
    <div className="chat">
      <div className="chat-toolbar">
        <label className="toggle">
          <input type="checkbox" checked={agentic} onChange={(e) => setAgentic(e.target.checked)} />
          Agentic mode (multi-step reasoning)
        </label>
        {messages.length > 0 && (
          <button className="link" onClick={() => setMessages([])}>
            Clear
          </button>
        )}
      </div>

      <div className="messages" ref={scroller}>
        {messages.length === 0 && (
          <div className="empty">
            {ready
              ? "Ask anything about the portal. Answers are grounded in crawled content with citations."
              : "Build a knowledge base above, then start chatting."}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">
              {m.steps && m.steps.length > 0 && (
                <details className="steps">
                  <summary>Reasoning ({m.steps.length} steps)</summary>
                  <ul>
                    {m.steps.map((s, j) => (
                      <li key={j}>
                        <b>{s.type}</b>: {s.detail}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
              <div className="content">{m.content || (busy ? "…" : "")}</div>
              {m.role === "assistant" && <Sources sources={m.sources} />}
            </div>
          </div>
        ))}
      </div>

      <form className="composer" onSubmit={send}>
        <input
          placeholder={ready ? "Ask a question…" : "Build a knowledge base first"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!ready || busy}
        />
        <button type="submit" disabled={!ready || busy}>
          Send
        </button>
      </form>
    </div>
  );
}

import React, { useEffect, useRef, useState } from "react";
import ApiCallCard from "./ApiCallCard.jsx";

export default function Chat({ messages, busy, disabled, onSend, placeholder }) {
  const [draft, setDraft] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const submit = (e) => {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy || disabled) return;
    onSend(text);
    setDraft("");
  };

  return (
    <div className="chat">
      <div className="messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <h2>Talk to your API in plain English</h2>
            <ul>
              <li>“Create a customer named John with email john@acme.com”</li>
              <li>“Find the order with id 42 and show its status”</li>
              <li>“Create a customer and place an order for 2 units of product A”</li>
            </ul>
            <p className="muted small">
              Write operations (POST/PUT/PATCH/DELETE) pause for your approval before running.
            </p>
          </div>
        )}

        {messages.map((m, i) => {
          if (m.role === "system-event") {
            return (
              <div key={i} className="event">
                {m.content}
              </div>
            );
          }
          return (
            <div key={i} className={`msg ${m.role}`}>
              <div className="avatar">{m.role === "user" ? "🧑" : "🤖"}</div>
              <div className="bubble">
                {m.content && <div className="bubble-text">{m.content}</div>}
                {m.apiCalls?.length > 0 && (
                  <div className="calls">
                    {m.apiCalls.map((c, j) => (
                      <ApiCallCard key={j} call={c} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {busy && (
          <div className="msg assistant">
            <div className="avatar">🤖</div>
            <div className="bubble">
              <div className="typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form className="composer" onSubmit={submit}>
        <textarea
          className="composer-input"
          rows={1}
          value={draft}
          placeholder={placeholder}
          disabled={disabled}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }}
        />
        <button className="btn primary" type="submit" disabled={busy || disabled}>
          Send
        </button>
      </form>
    </div>
  );
}

import { useState } from "react";
import { api, displaySource } from "../api/client.js";

export default function SearchPanel({ ready, onOpenPage }) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    setError("");
    try {
      const res = await api.search(query.trim());
      setHits(res.hits);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="search">
      <form onSubmit={run} className="search-form">
        <input
          placeholder={ready ? "Natural-language or keyword search…" : "Build a knowledge base first"}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={!ready}
        />
        <button disabled={!ready || busy}>{busy ? "Searching…" : "Search"}</button>
      </form>

      {error && <div className="err">⚠ {error}</div>}

      {hits && hits.length === 0 && <div className="empty">No matches.</div>}
      {hits && hits.length > 0 && (
        <ul className="hits">
          {hits.map((h) => (
            <li key={h.chunk_id}>
              <div className="hit-head">
                <button className="link strong" onClick={() => onOpenPage?.(h.page_id)}>
                  {h.title}
                </button>
                <span className="score">{h.score.toFixed(2)}</span>
              </div>
              {displaySource(h.url).href ? (
                <a className="url" href={h.url} target="_blank" rel="noreferrer">
                  {h.url}
                </a>
              ) : (
                <span className="url">{displaySource(h.url).label}</span>
              )}
              <p className="snippet">{h.text}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

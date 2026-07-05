import { useCallback, useEffect, useState } from "react";
import { api, displaySource } from "../api/client.js";

export default function ManagePanel({ ready, onChanged }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const load = useCallback(() => {
    api
      .sources()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load, ready]);

  async function run(label, fn, confirmMsg) {
    if (confirmMsg && !window.confirm(confirmMsg)) return;
    setBusy(label);
    setError("");
    try {
      await fn();
      load();
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  if (!ready) return <div className="empty">Build a knowledge base first — then you can manage and delete its sources here.</div>;

  const webItems = (data?.items || []).filter((i) => i.source === "web");
  const fileItems = (data?.items || []).filter((i) => i.source === "file");

  return (
    <div className="manage">
      {error && <div className="err">⚠ {error}</div>}

      <div className="manage-head">
        <div>
          {data && (
            <span className="muted">
              {data.web_pages} web page(s) · {data.file_pages} file(s)
            </span>
          )}
        </div>
        <button
          className="danger"
          disabled={!!busy}
          onClick={() =>
            run("clear", () => api.clearKb(), "Delete the ENTIRE knowledge base (all web pages and files)? This cannot be undone.")
          }
        >
          {busy === "clear" ? "Clearing…" : "Clear everything"}
        </button>
      </div>

      {webItems.length > 0 && (
        <section className="manage-group">
          <div className="manage-group-head">
            <h3>Web portal — {data.domain || "crawled site"}</h3>
            <button
              className="danger ghost"
              disabled={!!busy}
              onClick={() =>
                run(
                  "web",
                  () => api.deleteFromKb({ source: "web" }),
                  `Delete the crawled portal (${webItems.length} pages)?`
                )
              }
            >
              {busy === "web" ? "Deleting…" : `Delete portal (${webItems.length})`}
            </button>
          </div>
          <ul className="manage-list">
            {webItems.map((it) => (
              <li key={it.page_id}>
                <a href={it.url} target="_blank" rel="noreferrer" className="ellipsis">
                  {it.title}
                </a>
                <button
                  className="danger ghost sm"
                  disabled={!!busy}
                  onClick={() => run(it.page_id, () => api.deleteFromKb({ page_ids: [it.page_id] }))}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {fileItems.length > 0 && (
        <section className="manage-group">
          <div className="manage-group-head">
            <h3>Uploaded files</h3>
            <button
              className="danger ghost"
              disabled={!!busy}
              onClick={() =>
                run("file", () => api.deleteFromKb({ source: "file" }), `Delete all ${fileItems.length} uploaded file(s)?`)
              }
            >
              {busy === "file" ? "Deleting…" : `Delete all files (${fileItems.length})`}
            </button>
          </div>
          <ul className="manage-list">
            {fileItems.map((it) => (
              <li key={it.page_id}>
                <span className="ellipsis">{displaySource(it.url).label}</span>
                <button
                  className="danger ghost sm"
                  disabled={!!busy}
                  onClick={() => run(it.page_id, () => api.deleteFromKb({ page_ids: [it.page_id] }))}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {webItems.length === 0 && fileItems.length === 0 && <div className="empty">No sources in the knowledge base.</div>}
    </div>
  );
}

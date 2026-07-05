import { useEffect, useState } from "react";
import { api, displaySource } from "../api/client.js";

function TreeNode({ node, activeId, onSelect }) {
  const [open, setOpen] = useState(node.depth < 1);
  const hasChildren = node.children && node.children.length > 0;
  return (
    <li>
      <div className={`tree-row ${activeId === node.page_id ? "active" : ""}`}>
        {hasChildren ? (
          <button className="twisty" onClick={() => setOpen((o) => !o)}>
            {open ? "▾" : "▸"}
          </button>
        ) : (
          <span className="twisty spacer" />
        )}
        <button className="tree-label" onClick={() => onSelect(node.page_id)} title={node.url}>
          {node.title}
        </button>
      </div>
      {hasChildren && open && (
        <ul>
          {node.children.map((c) => (
            <TreeNode key={c.page_id} node={c} activeId={activeId} onSelect={onSelect} />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function NavigatePanel({ ready, selectedPageId, onSelect }) {
  const [tree, setTree] = useState([]);
  const [page, setPage] = useState(null);
  const [understanding, setUnderstanding] = useState(null);
  const [uBusy, setUBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    api.navigation().then(setTree).catch((e) => setError(e.message));
  }, [ready]);

  useEffect(() => {
    if (!selectedPageId) return;
    setUnderstanding(null);
    api.content(selectedPageId).then(setPage).catch((e) => setError(e.message));
  }, [selectedPageId]);

  async function analyze(mode) {
    if (!page) return;
    setUBusy(mode);
    setUnderstanding(null);
    try {
      const res = await api.understand({ page_id: page.page_id, mode });
      setUnderstanding({ mode, text: res.result });
    } catch (e) {
      setUnderstanding({ mode, text: `⚠ ${e.message}` });
    } finally {
      setUBusy("");
    }
  }

  if (!ready) return <div className="empty">Build a knowledge base to explore its structure.</div>;

  return (
    <div className="navigate">
      <aside className="tree">
        {error && <div className="err">⚠ {error}</div>}
        <ul className="tree-root">
          {tree.map((n) => (
            <TreeNode key={n.page_id} node={n} activeId={selectedPageId} onSelect={onSelect} />
          ))}
        </ul>
      </aside>

      <section className="page-view">
        {!page && <div className="empty">Select a page from the navigation tree.</div>}
        {page && (
          <>
            <nav className="crumbs">
              {page.breadcrumbs.map((b, i) => (
                <span key={b.page_id}>
                  {i > 0 && <span className="sep">›</span>}
                  <button className="link" onClick={() => onSelect(b.page_id)}>
                    {b.title}
                  </button>
                </span>
              ))}
            </nav>

            <h2>{page.title}</h2>
            {displaySource(page.url).href ? (
              <a className="url" href={page.url} target="_blank" rel="noreferrer">
                {page.url}
              </a>
            ) : (
              <span className="url">{displaySource(page.url).label}</span>
            )}

            <div className="understand-bar">
              {["summary", "topics", "insights", "classify"].map((m) => (
                <button key={m} onClick={() => analyze(m)} disabled={!!uBusy}>
                  {uBusy === m ? "…" : m}
                </button>
              ))}
            </div>

            {understanding && (
              <div className="understanding">
                <div className="u-title">{understanding.mode}</div>
                <pre>{understanding.text}</pre>
              </div>
            )}

            <article className="page-text">
              {page.text.split("\n\n").map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </article>

            {page.related.length > 0 && (
              <div className="related">
                <div className="related-title">Related content</div>
                <ul>
                  {page.related.map((r) => (
                    <li key={r.page_id}>
                      <button className="link" onClick={() => onSelect(r.page_id)}>
                        {r.title}
                      </button>
                      <span className="score"> · {r.score.toFixed(2)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}

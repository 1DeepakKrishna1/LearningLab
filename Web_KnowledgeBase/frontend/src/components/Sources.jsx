import { displaySource } from "../api/client.js";

export default function Sources({ sources }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="sources">
      <div className="sources-title">Sources</div>
      <ol>
        {sources.map((s) => {
          const d = displaySource(s.url);
          return (
            <li key={s.n}>
              {d.href ? (
                <a href={d.href} target="_blank" rel="noreferrer" title={s.url}>
                  {s.title || d.label}
                </a>
              ) : (
                <span title={d.label}>{s.title || d.label}</span>
              )}
              {typeof s.score === "number" && <span className="score"> · {s.score.toFixed(2)}</span>}
              {s.snippet && <div className="snippet">{s.snippet}</div>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

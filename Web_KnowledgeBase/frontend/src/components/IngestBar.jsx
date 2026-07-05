import { useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

export default function IngestBar({ status, onReady }) {
  const [mode, setMode] = useState("url"); // "url" | "files"
  const [url, setUrl] = useState("");
  const [depth, setDepth] = useState(2);
  const [maxPages, setMaxPages] = useState(100);
  const [files, setFiles] = useState([]);
  const [append, setAppend] = useState(true);
  const [startPage, setStartPage] = useState("");
  const [endPage, setEndPage] = useState("");
  const [accept, setAccept] = useState("");
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const poll = useRef(null);
  const fileInput = useRef(null);

  useEffect(() => () => clearInterval(poll.current), []);
  useEffect(() => {
    api
      .formats()
      .then((f) => setAccept(f.extensions.join(",")))
      .catch(() => {});
  }, []);

  function track(created) {
    setJob(created);
    clearInterval(poll.current);
    poll.current = setInterval(async () => {
      try {
        const j = await api.job(created.job_id);
        setJob(j);
        if (j.state === "done") {
          clearInterval(poll.current);
          onReady?.();
        } else if (j.state === "error") {
          clearInterval(poll.current);
        }
      } catch (err) {
        setError(err.message);
        clearInterval(poll.current);
      }
    }, 1200);
  }

  async function startUrl(e) {
    e.preventDefault();
    setError("");
    try {
      track(await api.ingest({ url: url.trim(), max_depth: Number(depth), max_pages: Number(maxPages) }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function startFiles(e) {
    e.preventDefault();
    setError("");
    if (!files.length) {
      setError("Choose one or more files.");
      return;
    }
    const sp = startPage ? Number(startPage) : null;
    const ep = endPage ? Number(endPage) : null;
    if (sp && ep && ep < sp) {
      setError("End page must be greater than or equal to start page.");
      return;
    }
    try {
      track(await api.ingestFiles(files, append, sp, ep));
    } catch (err) {
      setError(err.message);
    }
  }

  const busy = job && ["queued", "crawling", "indexing"].includes(job.state);

  return (
    <div className="ingest">
      <div className="ingest-modes">
        <button className={mode === "url" ? "seg active" : "seg"} onClick={() => setMode("url")} type="button">
          Crawl a website
        </button>
        <button className={mode === "files" ? "seg active" : "seg"} onClick={() => setMode("files")} type="button">
          Upload files
        </button>
      </div>

      {mode === "url" ? (
        <form onSubmit={startUrl} className="ingest-form">
          <input
            type="url"
            required
            placeholder="https://portal.example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <label>
            Depth
            <input type="number" min="0" max="6" value={depth} onChange={(e) => setDepth(e.target.value)} />
          </label>
          <label>
            Max pages
            <input type="number" min="1" max="2000" value={maxPages} onChange={(e) => setMaxPages(e.target.value)} />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Building…" : "Build knowledge base"}
          </button>
        </form>
      ) : (
        <form onSubmit={startFiles} className="ingest-form">
          <input
            ref={fileInput}
            type="file"
            multiple
            accept={accept || undefined}
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
          />
          <label>
            Start page
            <input
              type="number"
              min="1"
              placeholder="1"
              value={startPage}
              onChange={(e) => setStartPage(e.target.value)}
            />
          </label>
          <label>
            End page
            <input
              type="number"
              min="1"
              placeholder="all"
              value={endPage}
              onChange={(e) => setEndPage(e.target.value)}
            />
          </label>
          <label className="toggle inline">
            <input type="checkbox" checked={append} onChange={(e) => setAppend(e.target.checked)} />
            Add to existing
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Indexing…" : "Add files"}
          </button>
          {files.length > 0 && <span className="filecount">{files.length} file(s) selected</span>}
        </form>
      )}

      <div className="ingest-status">
        {error && <span className="err">⚠ {error}</span>}
        {job && !error && (
          <span className={`badge ${job.state}`}>
            {job.state}
            {busy && ` · ${job.pages_crawled} items · ${job.chunks_indexed} chunks`}
            {job.state === "done" && ` · ${job.pages_indexed} pages · ${job.chunks_indexed} chunks`}
            {job.error && ` · ${job.error}`}
          </span>
        )}
        {!job && status?.ready && (
          <span className="badge done">
            ready · {status.domain} · {status.page_count} pages · {status.chunk_count} chunks
          </span>
        )}
      </div>
      {mode === "files" && (
        <div className="hint">
          Supports PDF, Word (.docx), Excel (.xlsx/.xls), images (PNG/JPG…), and text/CSV/Markdown.
          Start/End page bound how much of each <b>PDF</b> is read (leave blank for all pages).
          Scanned PDFs with no text layer are read via image OCR — use a page range to keep that fast.
        </div>
      )}
    </div>
  );
}

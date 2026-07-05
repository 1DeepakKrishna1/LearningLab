// Typed-ish API client for the Knowledge Portal backend.
const BASE = "/api";

async function json(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  status: () => json("GET", "/status"),
  ingest: (payload) => json("POST", "/ingest", payload),
  formats: () => json("GET", "/ingest/formats"),
  ingestFiles: async (files, append = true, startPage = null, endPage = null) => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    fd.append("append", append ? "true" : "false");
    if (startPage) fd.append("start_page", String(startPage));
    if (endPage) fd.append("end_page", String(endPage));
    const res = await fetch(`${BASE}/ingest/files`, { method: "POST", body: fd });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json()).detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    return res.json();
  },
  job: (id) => json("GET", `/ingest/${id}`),
  sources: () => json("GET", "/sources"),
  deleteFromKb: (payload) => json("POST", "/kb/delete", payload),
  clearKb: () => json("DELETE", "/kb"),
  search: (query, top_k) => json("POST", "/search", { query, top_k }),
  navigation: () => json("GET", "/navigation"),
  content: (pageId) => json("GET", `/content/${pageId}`),
  chat: (message, history, top_k) => json("POST", "/chat", { message, history, top_k }),
  understand: (payload) => json("POST", "/understand", payload),
};

// Present a source URL: uploaded files (upload://name) become plain labels.
export function displaySource(url) {
  if (url && url.startsWith("upload://")) {
    return { label: `📄 ${url.slice("upload://".length)}`, href: null };
  }
  return { label: url, href: url };
}

// Streaming chat over Server-Sent Events. Calls onToken / onSources / onDone / onError.
export async function chatStream({ message, history, top_k }, handlers) {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, top_k }),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    handlers.onError?.(new Error(detail));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      const data = line.slice(5).trim();
      if (!data) continue;
      let evt;
      try {
        evt = JSON.parse(data);
      } catch {
        continue;
      }
      if (evt.type === "token") handlers.onToken?.(evt.text);
      else if (evt.type === "sources") handlers.onSources?.(evt.sources);
      else if (evt.type === "done") handlers.onDone?.();
      else if (evt.type === "error") handlers.onError?.(new Error(evt.error));
    }
  }
  handlers.onDone?.();
}

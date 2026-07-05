# LLM Knowledge Portal AI Agent

Turn **any web portal — or a set of documents** — into a conversational, source-grounded
knowledge agent. Point it at a URL (choose how deep to crawl) **or upload files** (PDF, Word,
Excel, images, text/CSV/Markdown), and the system builds one searchable knowledge base you can
search, chat with, navigate, and reason over.

- **Backend:** FastAPI + Python — async crawler, chunking, **OpenAI** embeddings, **FAISS** vector index, RAG + agentic tool-calling.
- **Frontend:** React (Vite) — ingest, streaming chat, semantic search, navigation tree + content understanding.
- **LLM:** OpenAI (`gpt-4o` by default). **Embeddings:** OpenAI `text-embedding-3-small`. **Vector store:** FAISS.

## Feature coverage (per the spec)

| # | Spec area | How it's delivered |
|---|-----------|--------------------|
| 1 | **Knowledge Search & Discovery** | Semantic FAISS search (`/api/search`), natural-language queries, context-aware retrieval, related-content discovery |
| 2 | **Conversational Assistance** | Streaming chat (`/api/chat/stream`) with full multi-turn history + context retention |
| 3 | **Knowledge Navigation** | N-level tree from crawl hierarchy (`/api/navigation`), breadcrumbs, related pages (`/api/content/{id}`) |
| 4 | **Question Answering** | Source-backed answers with inline `[n]` citations; agentic mode for policy/procedure/domain Q&A |
| 5 | **Content Understanding** | Summarize / topic extraction / key insights / classification (`/api/understand`) |
| 6 | **Agentic Reasoning** | Multi-step tool-calling loop (`/api/chat`): the model issues several searches, cross-references documents, and synthesizes |

## Architecture

```
            ┌──────────────┐   crawl (async BFS, depth/robots/domain bounded)
   URL ───► │   Crawler    │ ─────────────────────────────┐
            └──────────────┘                               ▼
                                          clean text → chunk → OpenAI embeddings
                                                              │
                                                              ▼
   React UI ◄── FastAPI ◄── RAG / Agent ◄────────── FAISS index + page store
   (chat,        (/api/*)    (OpenAI chat,                (persisted to ./data)
    search,                   tool loop,
    navigate)                 citations)
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key

## 1. Run the backend

```powershell
cd backend
# Windows
./run.ps1
```
```bash
cd backend            # macOS / Linux
./run.sh
```

Or manually:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # then edit .env and set OPENAI_API_KEY
uvicorn app.main:app --reload --port 9000
```

API docs: http://localhost:9000/docs

## 2. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api/*` to the backend on port 9000.

## Usage

1. **Build the knowledge base** — two sources, same downstream experience:
   - **Crawl a website**: paste a portal URL, set **Depth** and **Max pages**, click **Build knowledge base**.
   - **Upload files**: switch to *Upload files*, pick PDFs / Word / Excel / images / text, and click **Add files**. Keep *Add to existing* on to combine uploads with a crawled site (or other uploads); turn it off to start fresh. Images and scanned content are transcribed via the OpenAI vision model. Each file becomes a page — so Chat, Search and Navigate all work over it. Progress is polled live.
2. **Chat** — ask questions; answers stream with citations. Toggle **Agentic mode** for multi-step reasoning across documents.
3. **Search** — semantic search over the portal; click a result to open the page.
4. **Navigate** — browse the N-level tree, read pages with breadcrumbs, run summary / topics / insights / classify, and jump to related content.
5. **Manage** — review everything in the knowledge base and delete it: remove the whole crawled portal, delete all uploaded files, drop an individual page/file, or **Clear everything**.

## Configuration

All settings live in `backend/.env` (see `.env.example`). Key ones:

| Var | Default | Meaning |
|-----|---------|---------|
| `OPENAI_API_KEY` | — | **Required.** |
| `LLM_MODEL` | `gpt-4o` | OpenAI chat model. |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model. |
| `MAX_CRAWL_DEPTH` | `2` | Navigation levels to follow from the seed (configurable per request too). |
| `MAX_PAGES` | `200` | Crawl cap. |
| `SAME_DOMAIN_ONLY` | `true` | Stay on the seed's domain. |
| `RESPECT_ROBOTS` | `true` | Honor `robots.txt`. |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1200` / `200` | Chunking. |
| `TOP_K` | `6` | Passages retrieved per query. |
| `DATA_DIR` | `./data` | Where the FAISS index + page store persist. |

`OPENAI_BASE_URL` can point the SDK at a compatible gateway.

## Notes & design choices

- **Embeddings via OpenAI** (no local model download). FAISS (`IndexFlatIP` over L2-normalized vectors = cosine) is the vector store, persisted to `DATA_DIR` and reloaded on startup.
- **Two chat paths:** `/api/chat/stream` (fast single-pass RAG, token streaming) for the UI, and `/api/chat` (agentic tool-calling loop) for multi-step reasoning and cross-document analysis.
- **Citations** are grounded: the model is given numbered sources and instructed to cite `[n]`; the API returns the matching source list.
- **Single active knowledge base.** A web crawl replaces the KB; file uploads append (toggle off *Add to existing* to replace). Use the **Manage** tab (or `DELETE /api/kb`, `POST /api/kb/delete`) to remove sources. Deletions rebuild the FAISS index from the retained vectors (reconstructed in-place, no re-embedding). The ingest job registry is in-memory (single process) — use Redis + a shared store to scale horizontally.
- Be a responsible crawler: respect target sites' terms and `robots.txt`.
```

# SLLM — Local Small LLM with RAG + FastAPI + React

Build your own **small local LLM** assistant over a folder of mixed documents
(PDFs, images, CSV, XLS), served behind a FastAPI gateway and a React chatbot.
Everything runs **offline on your laptop** via [Ollama](https://ollama.com).

Two ways to make the model "yours" (per the design doc):

- **RAG (default, recommended):** ingest your documents into a vector store; the
  backend retrieves relevant passages at query time and answers from them with
  citations. Best for factual, grounded Q&A. Runs on CPU.
- **Fine-tuning (Path B, optional):** QLoRA fine-tune a base model on a dataset
  synthesized from your docs to shape its *tone/behaviour*. Complements RAG;
  needs a GPU. See [`Datapipeline/finetune/`](Datapipeline/finetune/README.md).

```
SLLM/
├── Datapipeline/        # ingest docs -> chunks -> embeddings -> Chroma vector store
│   ├── ingest.py            # main RAG ingestion script
│   ├── loaders.py           # PDF / image(OCR) / CSV / XLS / text extractors
│   ├── chunker.py
│   ├── config.py
│   ├── Modelfile            # Path A: bake tone/params into a named Ollama model
│   ├── data/                # <-- drop your documents here
│   └── finetune/            # Path B: QLoRA fine-tuning (optional, GPU)
├── Backend/             # FastAPI gateway: retrieval + streaming chat over Ollama
│   ├── main.py
│   ├── rag.py
│   └── config.py
├── frontend/            # React (Vite) streaming chatbot UI
└── vectorstore/         # created by the pipeline (Chroma); shared with Backend
```

---

## Prerequisites (install once)

1. **Ollama** — https://ollama.com/download. Then pull the models:
   ```bash
   ollama pull llama3.2:3b        # chat model (small, fits ~8GB RAM at Q4)
   ollama pull nomic-embed-text   # embedding model for RAG
   ```
   Match the chat model to your RAM (see the design doc): `llama3.2:3b` for 8GB,
   `qwen3:7b` / `gemma3:12b` for 16GB. Change it via `SLLM_CHAT_MODEL`.
2. **Python 3.10+**
3. **Node.js 18+** (for the React frontend)
4. *(Optional, for image OCR)* **Tesseract OCR** —
   https://github.com/UB-Mannheim/tesseract/wiki (Windows installer). Without it,
   images are skipped with a warning; PDFs/CSV/XLS still work.

> **Windows note:** commands below show PowerShell. Run `ollama serve` in its own
> terminal (or it runs as a background service after install).

---

## Step 1 — Build the knowledge base (Data pipeline)

```powershell
cd Datapipeline
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Put your PDFs / images / .csv / .xls(x) into Datapipeline\data\  (or use --folder)
python ingest.py
```

This extracts text from every supported file, chunks it, embeds each chunk with
`nomic-embed-text`, and writes a persistent Chroma store to `../vectorstore/`.
Re-run anytime to rebuild; use `--keep` to append, `--folder PATH` for a different
source folder.

**Optional — Path A (no training):** bake a system prompt/params into a named
model and use it as the chat model:
```powershell
ollama create my-slm -f Modelfile
$env:SLLM_CHAT_MODEL = "my-slm"
```

**Optional — Path B (fine-tuning):** see [`finetune/README.md`](Datapipeline/finetune/README.md).

---

## Step 2 — Start the Backend (FastAPI)

```powershell
cd ..\Backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Verify:
- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/health  → should show `"knowledge_base_ready": true`

Endpoints:
| Method | Path      | Purpose                                            |
|--------|-----------|----------------------------------------------------|
| GET    | `/health` | model names + whether the vector store has data    |
| POST   | `/chat`   | grounded answer as JSON `{reply, sources}`         |
| POST   | `/stream` | grounded answer streamed (newline-delimited JSON)  |

> The Backend reads the **same** `vectorstore/` the pipeline wrote. If you set a
> custom `SLLM_VECTORSTORE_DIR` or `SLLM_EMBED_MODEL` during ingestion, set the
> identical values for the Backend.

---

## Step 3 — Start the Frontend (React chatbot)

```powershell
cd ..\frontend
npm install
npm run dev
```

Open http://localhost:5173. The header shows backend/model status; answers stream
in token-by-token with the source filenames used. To point at a non-default
backend, copy `.env.example` to `.env` and set `VITE_API_URL`.

---

## Configuration (environment variables)

| Variable                | Default                  | Used by        |
|-------------------------|--------------------------|----------------|
| `OLLAMA_HOST`           | `http://localhost:11434` | pipeline, backend |
| `SLLM_CHAT_MODEL`       | `llama3.2:3b`            | backend        |
| `SLLM_EMBED_MODEL`      | `nomic-embed-text`       | pipeline, backend |
| `SLLM_DOCS_FOLDER`      | `Datapipeline/data`      | pipeline       |
| `SLLM_VECTORSTORE_DIR`  | `<project>/vectorstore`  | pipeline, backend |
| `SLLM_COLLECTION`       | `sllm_docs`              | pipeline, backend |
| `SLLM_TOP_K`            | `4`                      | backend        |
| `SLLM_CHUNK_SIZE`       | `1000`                   | pipeline       |
| `SLLM_CHUNK_OVERLAP`    | `150`                    | pipeline       |
| `VITE_API_URL`          | `http://localhost:8000`  | frontend       |

---

## Production notes (from the design doc)

- **Concurrency:** a single Ollama instance is largely sequential. The Backend
  uses `async` endpoints + the async Ollama client, but don't expect many
  simultaneous users on a laptop. For throughput, swap Ollama for `llama.cpp`'s
  server or vLLM — the FastAPI layer stays unchanged.
- **Timeouts / context limits:** long prompts can exceed `num_ctx`. The Backend
  caps input length (`SLLM_MAX_INPUT_CHARS`) before it reaches the model.
- **Offline:** once the models are pulled, the whole chain runs without internet.
```

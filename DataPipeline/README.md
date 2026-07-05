# DataPipeline

Production-grade, modular Python pipeline that processes PDF documents from multiple sources and generates structured AI-ready outputs using GroQ LLM, LangGraph orchestration, and FAISS vector embeddings.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT SOURCES                               │
│   Local FS  │  Google Drive (OAuth2)  │  SharePoint (MS Graph)     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                                 │
│  File Discovery → SHA-256 Deduplication → Raw Copy → State Tracking│
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 LANGGRAPH PIPELINE (State Machine)                  │
│                                                                     │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────┐    │
│  │ Extract │──▶│ Process │──▶│  Embed  │──▶│   AI Enrichment │    │
│  │         │   │         │   │         │   │                 │    │
│  │PyMuPDF  │   │ Cleaner │   │sentence │   │ Knowledge Graph │    │
│  │pdfplumb │   │ Chunker │   │-xformers│   │ FAQ Generation  │    │
│  │EasyOCR  │   │ NER/KW  │   │  FAISS  │   │ DOK Questions   │    │
│  └─────────┘   └─────────┘   └─────────┘   └────────┬────────┘    │
│                                                      │ GroQ LLM    │
│                               Error edges at each node             │
└──────────────────────────────────────────┬──────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     STRUCTURED OUTPUT                               │
│  output/                                                            │
│  ├── raw/              Original PDFs (content-addressed)            │
│  ├── extracted/        Text + Tables + Image metadata (JSON)        │
│  ├── processed/        Chunks + NER + Keywords (JSON)               │
│  ├── embeddings/       FAISS index + chunk metadata                 │
│  ├── knowledge_graph/  Entities + Relationships (JSON)              │
│  ├── faq/              Q&A pairs (JSON)                             │
│  └── questions/        DOK Level 1-4 questions (JSON)              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
DataPipeline/
├── config/
│   ├── config.yaml          # Main pipeline configuration
│   ├── prompts.yaml         # GroQ LLM prompt templates
│   └── logging.yaml         # Structured logging config
├── src/
│   ├── models/schemas.py    # Pydantic v2 data models
│   ├── pipeline/
│   │   └── orchestrator.py  # LangGraph state machine
│   ├── ingestion/           # Local, GDrive, SharePoint ingesters
│   ├── extraction/          # Text, table, image, OCR extractors
│   ├── processing/          # Cleaner, semantic chunker, metadata extractor
│   ├── embedding/           # sentence-transformers + FAISS vector store
│   ├── enrichment/          # GroQ client, KG / FAQ / DOK generators
│   ├── storage/             # Phase-wise JSON file store
│   └── utils/               # Logger, metrics, retry, security
├── scripts/
│   ├── run_pipeline.py      # CLI entrypoint
│   ├── load_sample_data.py  # Demo data loader
│   └── create_sample_pdfs.py
├── tests/                   # pytest test suite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Quick Start (Local)

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd DataPipeline
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — add your GROQ_API_KEY at minimum
```

### 4. Load sample data and run demo

```bash
# Creates 3 sample PDFs, runs extraction + embedding (no GroQ needed)
python scripts/load_sample_data.py --skip-enrich

# Full run with AI enrichment (requires GROQ_API_KEY)
python scripts/load_sample_data.py
```

### 5. Process your own PDFs

```bash
# Copy PDFs to ./input, then:
python scripts/run_pipeline.py run --input ./input

# Check status
python scripts/run_pipeline.py status

# Semantic search across processed docs
python scripts/run_pipeline.py search --query "machine learning"
```

---

## Docker

```bash
# Build and run
cp .env.example .env   # add GROQ_API_KEY
docker-compose up pipeline

# With Prometheus + Grafana monitoring
docker-compose --profile monitoring up

# Grafana: http://localhost:3000  (admin/admin)
# Prometheus: http://localhost:9090
# Pipeline metrics: http://localhost:8000
```

---

## Configuration

All settings live in `config/config.yaml` and are overridable via environment variables (see `.env.example`).

| Key | Default | Description |
|-----|---------|-------------|
| `pipeline.batch_size` | 10 | Documents per batch |
| `extraction.text.backend` | `pymupdf` | `pymupdf` or `pdfplumber` |
| `extraction.tables.backend` | `pdfplumber` | `pdfplumber`, `camelot`, or `tabula` |
| `extraction.images.ocr.enabled` | `true` | Enable EasyOCR on extracted images |
| `processing.chunking.strategy` | `semantic` | `semantic`, `fixed`, or `sentence` |
| `processing.chunking.chunk_size` | `512` | Max words per chunk |
| `embedding.model` | `all-MiniLM-L6-v2` | sentence-transformers model name |
| `enrichment.groq.model` | `llama3-70b-8192` | GroQ model ID |

---

## Input Sources

### Local Filesystem (default)
```bash
python scripts/run_pipeline.py run --input ./my_pdfs
```

### Google Drive
1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable the Drive API and download OAuth credentials to `config/gdrive_credentials.json`
3. Set `GDRIVE_FOLDER_ID` in `.env`
4. Run: `python scripts/run_pipeline.py run --source gdrive`

### SharePoint
1. Register an app in [Azure Portal](https://portal.azure.com) with `Files.Read.All` permission
2. Set `SHAREPOINT_TENANT_ID`, `SHAREPOINT_CLIENT_ID`, `SHAREPOINT_CLIENT_SECRET`, `SHAREPOINT_DRIVE_ID` in `.env`
3. Run: `python scripts/run_pipeline.py run --source sharepoint`

---

## Output Format

Every output file is JSON, traceable by `doc_id` (SHA-256 of file content).

### `extracted/<doc_id>.json`
```json
{
  "doc_id": "abc123...",
  "file_name": "report.pdf",
  "total_pages": 12,
  "raw_text": "...",
  "tables": [{"page": 1, "headers": ["Col A", "Col B"], "rows": [...]}],
  "images": [{"page": 2, "ocr_text": "chart showing..."}]
}
```

### `knowledge_graph/<doc_id>.json`
```json
{
  "entities": [{"id": "e1", "name": "TensorFlow", "type": "PRODUCT"}],
  "relationships": [{"source": "e1", "target": "e2", "relation": "created_by"}],
  "attributes": [{"entity_id": "e1", "key": "language", "value": "Python"}]
}
```

### `faq/<doc_id>.json`
```json
[
  {"question": "What is supervised learning?", "answer": "...", "confidence": 0.95}
]
```

### `questions/<doc_id>.json`
```json
{
  "level_1": [{"question": "What is a neural network?", "answer": "...", "bloom": "Remember"}],
  "level_2": [{"question": "Explain backpropagation", "answer": "...", "bloom": "Understand"}],
  "level_3": [{"question": "Analyze overfitting", "answer": "...", "bloom": "Analyze"}],
  "level_4": [{"question": "Design an image classifier", "answer": "...", "bloom": "Create"}]
}
```

---

## Running Tests

```bash
# All tests
pytest

# With coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Specific module
pytest tests/test_processing.py -v

# Skip slow embedding tests
pytest -k "not TestEmbedder and not TestFAISS"
```

---

## Observability

- **Structured logging** — JSON logs to `logs/pipeline.log` via `structlog`
- **Prometheus metrics** — exposed on `:8000/metrics`
  - `pipeline_docs_ingested_total` — by source type
  - `pipeline_stage_duration_seconds` — histogram per stage
  - `pipeline_docs_failed_total` — by stage
  - `pipeline_embeddings_generated_total`
  - `pipeline_llm_calls_total` — by call type and status
- **Idempotency** — state tracked in `output/.pipeline_state.json`; re-running skips completed docs
- **Retry** — tenacity-backed exponential backoff on all external API calls

---

## Security

- All secrets loaded via `pydantic-settings` from `.env` — never hardcoded
- API keys exposed only as `SecretStr` — not logged or serialised
- SharePoint uses MSAL client credentials flow (app-only, no user tokens)
- Docker image runs as non-root user (`pipeline`, uid 1001)
- `.gitignore` excludes credentials and `.env`

---

## Extending the Pipeline

### Add a new ingestion source
1. Subclass `BaseIngester` in `src/ingestion/`
2. Implement `discover()` and `_fetch_local()`
3. Register in `scripts/run_pipeline.py`

### Add a new enrichment step
1. Create a generator class in `src/enrichment/`
2. Add a prompt template in `config/prompts.yaml`
3. Add a LangGraph node in `src/pipeline/orchestrator.py`

### Swap embedding model
Set `EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2` in `.env` (any sentence-transformers model).

### Use Pinecone instead of FAISS
Call `vector_store.export_pinecone_format(records)` and upsert via the Pinecone client.

---

## Requirements

- Python 3.10+
- GroQ API key (for AI enrichment)
- Java (for tabula-py, optional)
- Ghostscript + Poppler (for camelot, optional)
- Tesseract OCR (optional, EasyOCR is used by default)

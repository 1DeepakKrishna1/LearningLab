# Semantic Cache

A production-quality semantic cache that reduces LLM API calls by reusing answers to semantically similar questions.

**Stack:** HuggingFace embeddings (local) · Groq LLM · Redis TTL · NumPy cosine similarity

---

## Getting Started from Scratch

### 1. Prerequisites

- Python 3.11+
- A running Redis instance (see [Redis Setup](#redis-setup) below)

### 2. Clone and create a virtual environment

```bash
git clone <repo-url>
cd Semantic-Cache

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> `torch` and `transformers` are large packages. The first install may take a few minutes.

### 4. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=gsk_...          # from console.groq.com
```

All other values have sensible defaults. See [Configuration](#configuration) for the full reference.

### 5. Run the demo

```bash
python example_usage.py
```

The demo uses a mock LLM and a deterministic in-memory embedder — **no Groq key required**. It exercises all three cache strategies (direct hit, RAG, LLM fallback) and opens an interactive prompt at the end.

---

## Redis Setup

### Option A — Windows portable binary (Redis 3.0, simplest)

1. Download `Redis-x64-3.0.504.zip` from the [microsoftarchive/redis releases](https://github.com/microsoftarchive/redis/releases)
2. Extract to a folder, e.g. `C:\Redis`
3. Start the server:

```powershell
Start-Process -FilePath "C:\Redis\redis-server.exe" `
              -ArgumentList "C:\Redis\redis.windows.conf" `
              -WindowStyle Hidden
```

4. Verify it is running:

```powershell
C:\Redis\redis-cli.exe ping   # should print: PONG
```

To stop Redis: open Task Manager and end the `redis-server.exe` process.

### Option B — Docker (Redis 7, recommended for production parity)

```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### Option C — macOS / Linux

```bash
# macOS
brew install redis && brew services start redis

# Ubuntu / Debian
sudo apt install redis-server && sudo systemctl start redis
```

---

## How It Works

Every query goes through a three-stage decision tree:

```
query
  │
  ▼
embed (HuggingFace, local)
  │
  ▼
cosine search (numpy, in-memory index)
  │
  ├─ top-1 similarity ≥ HIGH_TH (0.9) ──→ DIRECT HIT    return cached answer
  │
  ├─ any top-K similarity ≥ LOW_TH (0.7) ─→ RAG          pass cached Q/A pairs
  │                                                        as context to Groq LLM
  └─ no match ────────────────────────────→ LLM FALLBACK  call Groq, cache result
```

### No Stale Index

Redis TTL expires cache entries automatically. The in-memory vector index stays in sync via two complementary mechanisms:

1. **Proactive** — subscribes to `__keyevent:expired` keyspace notifications; removes the vector from the index within milliseconds of expiry.
2. **Reactive** — before returning any hit, validates the entry still exists in Redis. Stale index entries are evicted on the spot.

---

## Architecture

```
semantic_cache/
├── cache.py          # SemanticCache orchestrator + GroqLLMCaller
├── config.py         # Settings (pydantic-settings, env-var driven)
├── exceptions.py     # Typed exception hierarchy
├── listener.py       # ExpiryListener background task (keyspace pubsub)
├── embedders/
│   └── __init__.py   # EmbedderProtocol + HuggingFaceEmbedder
├── index/
│   └── vector_index.py  # In-memory numpy cosine index (asyncio.Lock)
└── store/
    ├── redis_store.py   # Redis I/O: HSET, EXPIRE, pubsub, prune
    └── schemas.py       # CacheEntry, CacheResponse, SearchResult (Pydantic)
```

### Key design choices

| Concern | Decision |
|---|---|
| Vector similarity | NumPy `matrix @ query_vec` (BLAS DGEMV). Pre-normalised rows → cosine = dot product, O(N). |
| Top-K selection | `np.argpartition` — O(N), not O(N log N). |
| Async safety | Single `asyncio.Lock` in `VectorIndex` serialises all mutations. |
| Redis storage | Each entry is a Hash with embedding + answer + metadata + TTL via native `EXPIRE`. A permanent Set tracks live entry IDs for cold-start rebuild. |
| Crash recovery | New entries are written to Redis *before* being added to the index. On restart, the index is rebuilt from Redis. |

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```env
# Redis
REDIS_URL=redis://localhost:6379/0
KEY_PREFIX=semcache

# Similarity thresholds
HIGH_TH=0.9      # direct cache hit
LOW_TH=0.7       # RAG context threshold
TOP_K=5          # candidates to consider for RAG

# TTL
DEFAULT_TTL=3600  # seconds; 0 = no expiry

# Embedder backend ("demo" = hash-based, no download; "hf" = real semantic model)
EMBEDDER=demo

# HuggingFace embeddings (runs locally, no API key)
HF_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
VECTOR_DIM=384

# LLM backend ("mock" = no API key; "groq" = requires GROQ_API_KEY)
LLM_BACKEND=mock

# Groq LLM
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile
LLM_MAX_TOKENS=1024
```

### Backend combinations

| `EMBEDDER` | `LLM_BACKEND` | Semantic matching? | API key needed? |
|---|---|---|---|
| `demo` | `mock` | No (hash vectors) | No |
| `hf` | `mock` | **Yes** | No |
| `demo` | `groq` | No | Yes |
| `hf` | `groq` | **Yes** | Yes |

> `EMBEDDER=hf` automatically uses the model's real output dimension — `VECTOR_DIM` is set at runtime and does not need to be changed manually.

### Groq model options

| Model | Notes |
|---|---|
| `llama-3.3-70b-versatile` | Default. Strong general-purpose. |
| `llama-3.1-8b-instant` | Fastest, lower cost. |
| `mixtral-8x7b-32768` | Large context window (32K). |
| `gemma2-9b-it` | Google Gemma 2, efficient. |

### HuggingFace model options

| Model | Dim | Notes |
|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Default. Fast, good quality. |
| `sentence-transformers/all-mpnet-base-v2` | 768 | Higher quality, slower. |
| `BAAI/bge-small-en-v1.5` | 384 | Strong retrieval-focused model. |
| `BAAI/bge-large-en-v1.5` | 1024 | Best quality, largest. |

> Set `VECTOR_DIM` to match the model's output dimension.

---

## Usage

### Basic

```python
import asyncio
from semantic_cache import GroqLLMCaller, SemanticCache, Settings

async def main():
    settings = Settings()  # reads from .env
    llm = GroqLLMCaller.from_settings(settings)

    async with SemanticCache.create(settings) as cache:
        resp = await cache.query("What is Python?", llm)
        print(resp.strategy)   # "llm_fallback" (first call, cold cache)
        print(resp.answer)

        resp2 = await cache.query("What is Python?", llm)
        print(resp2.strategy)  # "direct_hit" (identical query)

        resp3 = await cache.query("Tell me about Python", llm)
        print(resp3.strategy)  # "rag_generation" (similar query)

asyncio.run(main())
```

### Custom embedder

Inject any object that satisfies `EmbedderProtocol`:

```python
from semantic_cache.embedders import HuggingFaceEmbedder
from semantic_cache.index.vector_index import VectorIndex
from semantic_cache.store.redis_store import RedisStore

embedder = HuggingFaceEmbedder(model_name="BAAI/bge-small-en-v1.5")
settings = Settings(VECTOR_DIM=384)

store = RedisStore(redis_url=settings.redis_url, key_prefix=settings.key_prefix)
index = VectorIndex(dim=settings.vector_dim)
cache = SemanticCache(settings=settings, embedder=embedder, store=store, index=index)

async with cache:
    resp = await cache.query("What is Rust?", llm)
```

### Manual cache population

```python
async with SemanticCache.create(settings) as cache:
    entry_id = await cache.set(
        question="What is the capital of France?",
        answer="Paris.",
        ttl=86400,  # 24 hours
    )
    print("Stored:", entry_id)
```

### Invalidation and flush

```python
async with SemanticCache.create(settings) as cache:
    # Remove one entry
    await cache.invalidate(entry_id)

    # Remove all entries
    await cache.flush()
```

### Stats

```python
async with SemanticCache.create(settings) as cache:
    print(await cache.stats())
    # {
    #   "index_size": 42,
    #   "high_th": 0.9,
    #   "low_th": 0.7,
    #   "top_k": 5,
    #   "default_ttl": 3600,
    #   "vector_dim": 384
    # }
```

---

## Running Tests

Unit tests (no Redis, no external APIs):

```bash
pytest tests/test_vector_index.py -v
```

Integration tests (requires a local Redis on `localhost:6379`):

```bash
# Docker
docker run -d -p 6379:6379 redis:7-alpine

# Windows portable binary (see Redis Setup above)
Start-Process "C:\Redis\redis-server.exe" -ArgumentList "C:\Redis\redis.windows.conf" -WindowStyle Hidden

pytest tests/test_cache.py -v -m integration
```

---

## Redis Keyspace Notifications

The stale-index listener requires keyspace notifications to be enabled. The cache does this automatically at startup via `CONFIG SET notify-keyspace-events Kx`.

On managed Redis services (AWS ElastiCache, Redis Cloud) `CONFIG SET` may be restricted. In that case:

- Enable `notify-keyspace-events` in your service's configuration panel (set it to `Kx` or `KEx`).
- Or rely solely on **validation-on-read** — the cache remains correct either way; the in-memory index just takes longer to shrink after entries expire.

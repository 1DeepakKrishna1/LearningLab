"""Backend configuration. Mirrors the pipeline's vector-store settings so both
sides agree on where the embeddings live and which embedding model produced them.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Must match the data pipeline.
VECTORSTORE_DIR = Path(os.getenv("SLLM_VECTORSTORE_DIR", PROJECT_ROOT / "vectorstore"))
COLLECTION_NAME = os.getenv("SLLM_COLLECTION", "sllm_docs")
EMBED_MODEL = os.getenv("SLLM_EMBED_MODEL", "nomic-embed-text")

# Ollama connection + the small chat model used to generate answers.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CHAT_MODEL = os.getenv("SLLM_CHAT_MODEL", "llama3.2:3b")  # or "my-slm" from the Modelfile

# Retrieval / generation knobs.
TOP_K = int(os.getenv("SLLM_TOP_K", "4"))
TEMPERATURE = float(os.getenv("SLLM_TEMPERATURE", "0.3"))
NUM_CTX = int(os.getenv("SLLM_NUM_CTX", "8192"))
MAX_INPUT_CHARS = int(os.getenv("SLLM_MAX_INPUT_CHARS", "4000"))  # guard against huge prompts

SYSTEM_PROMPT = os.getenv(
    "SLLM_SYSTEM_PROMPT",
    "You are a helpful assistant for Exelcius. Answer using only the provided "
    "context. If the answer is not contained in the context, say you don't know. "
    "Be concise and cite the source filenames you used.",
)

# CORS origins allowed to call this API (the React dev server).
CORS_ORIGINS = os.getenv(
    "SLLM_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")

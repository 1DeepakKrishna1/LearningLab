"""Shared configuration for the data pipeline.

Everything is overridable through environment variables so the same code runs
on any laptop without editing source. The vector store location is shared with
the Backend (set SLLM_VECTORSTORE_DIR identically in both, or rely on the
default which points at <project>/vectorstore).
"""
import os
from pathlib import Path

# <project>/Datapipeline/config.py  ->  parents[1] == <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Folder that holds the source documents you want the SLLM to learn from.
# Drop your PDFs / images / .csv / .xls(x) here, or point this elsewhere.
DOCS_FOLDER = Path(os.getenv("SLLM_DOCS_FOLDER", PROJECT_ROOT / "Datapipeline/data"))

# Where the Chroma vector store is persisted (read by the Backend at query time).
VECTORSTORE_DIR = Path(os.getenv("SLLM_VECTORSTORE_DIR", PROJECT_ROOT / "vectorstore"))

# Logical name of the collection inside Chroma.
COLLECTION_NAME = os.getenv("SLLM_COLLECTION", "sllm_docs")

# Ollama connection + models (all local, all offline once pulled).
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("SLLM_EMBED_MODEL", "nomic-embed-text")

# Chunking. ~1000 chars with overlap keeps chunks inside the embed context
# while preserving enough surrounding text for good retrieval.
CHUNK_SIZE = int(os.getenv("SLLM_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("SLLM_CHUNK_OVERLAP", "150"))

# File types the pipeline knows how to read.
SUPPORTED_SUFFIXES = {
    ".pdf",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp",
    ".csv",
    ".xls", ".xlsx",
    ".txt", ".md",
}

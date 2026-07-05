"""Retrieval layer: turn a user question into grounded prompt messages.

Loads the Chroma collection built by the data pipeline, embeds the incoming
question with the same embedding model, retrieves the top-k chunks, and builds
the chat messages (system + context + question) for the Ollama chat model.
"""
from typing import Dict, List, Tuple

import chromadb
from ollama import Client

import config

_ollama = Client(host=config.OLLAMA_HOST)
_collection = None


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(config.VECTORSTORE_DIR))
        _collection = client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def is_ready() -> bool:
    try:
        return _get_collection().count() > 0
    except Exception:
        return False


def retrieve(query: str, k: int = None) -> List[Dict]:
    """Return the top-k matching chunks as [{text, source, distance}]."""
    k = k or config.TOP_K
    collection = _get_collection()
    if collection.count() == 0:
        return []

    embedding = _ollama.embeddings(model=config.EMBED_MODEL, prompt=query)["embedding"]
    res = collection.query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append({"text": doc, "source": meta.get("source", "?"), "distance": dist})
    return hits


def build_messages(query: str) -> Tuple[List[Dict], List[str]]:
    """Build chat messages grounded in retrieved context.

    Returns (messages, sources) where sources is the de-duplicated list of
    source filenames used, for display in the UI.
    """
    query = query[: config.MAX_INPUT_CHARS]
    hits = retrieve(query)

    if not hits:
        context = "(no relevant context was found in the knowledge base)"
        sources: List[str] = []
    else:
        blocks = [f"[Source: {h['source']}]\n{h['text']}" for h in hits]
        context = "\n\n---\n\n".join(blocks)
        seen, sources = set(), []
        for h in hits:
            if h["source"] not in seen:
                seen.add(h["source"])
                sources.append(h["source"])

    messages = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}",
        },
    ]
    return messages, sources

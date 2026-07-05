"""A small, dependency-free character chunker with overlap."""
from typing import List


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

    chunks: List[str] = []
    start, n = 0, len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
    return chunks

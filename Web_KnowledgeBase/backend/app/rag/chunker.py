"""Split page text into overlapping, paragraph-aware chunks."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    index: int


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[Chunk]:
    text = text.strip()
    if not text:
        return []

    # Greedy paragraph packing, then hard-wrap any oversized paragraph.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units: list[str] = []
    for p in paragraphs:
        if len(p) <= chunk_size:
            units.append(p)
        else:
            for i in range(0, len(p), chunk_size):
                units.append(p[i : i + chunk_size])

    chunks: list[str] = []
    buf = ""
    for unit in units:
        if not buf:
            buf = unit
        elif len(buf) + len(unit) + 2 <= chunk_size:
            buf = f"{buf}\n\n{unit}"
        else:
            chunks.append(buf)
            if overlap > 0 and len(buf) > overlap:
                tail = buf[-overlap:]
                buf = f"{tail}\n\n{unit}"
            else:
                buf = unit
    if buf:
        chunks.append(buf)

    return [Chunk(text=c, index=i) for i, c in enumerate(chunks)]

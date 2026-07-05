"""The in-memory + on-disk knowledge base: pages, navigation tree, vector index."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import urlparse

import numpy as np

from ..config import get_settings
from . import embeddings
from .vectorstore import VectorStore


def page_id_for(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


@dataclass
class Page:
    page_id: str
    url: str
    title: str
    text: str
    depth: int
    parent_url: Optional[str]
    headings: list[str] = field(default_factory=list)
    source: str = "web"  # "web" (crawled) or "file" (uploaded)


@dataclass
class KBMeta:
    seed_url: str = ""
    domain: str = ""
    max_depth: int = 0
    embedding_model: str = ""


class KnowledgeBase:
    """Singleton holder for the active knowledge base."""

    def __init__(self) -> None:
        self.pages: dict[str, Page] = {}
        self.store: Optional[VectorStore] = None
        self.meta = KBMeta()
        self._lock = threading.Lock()

    # ---- lifecycle ----
    def reset(self) -> None:
        with self._lock:
            self.pages = {}
            self.store = None
            self.meta = KBMeta()

    @property
    def ready(self) -> bool:
        return self.store is not None and self.store.size > 0

    def set(self, pages: dict[str, Page], store: VectorStore, meta: KBMeta) -> None:
        with self._lock:
            self.pages = pages
            self.store = store
            self.meta = meta

    def add(self, pages: dict[str, Page], vectors, records) -> None:
        """Append pages + their vectors to the existing index (creates one if empty)."""
        with self._lock:
            if self.store is None:
                dim = int(vectors.shape[1]) if len(vectors) else embeddings.dimension(
                    self.meta.embedding_model or get_settings().embedding_model
                )
                self.store = VectorStore(dim=dim)
            self.pages.update(pages)
            self.store.add(vectors, records)

    # ---- deletion ----
    def sources_list(self) -> list[Page]:
        return sorted(
            self.pages.values(),
            key=lambda p: (0 if p.source == "web" else 1, p.depth, p.title.lower()),
        )

    def delete_pages(self, page_ids) -> tuple[int, int]:
        """Remove pages (and their chunks). Returns (pages_removed, chunks_removed)."""
        with self._lock:
            ids = {pid for pid in page_ids if pid in self.pages}
            if not ids:
                return (0, 0)
            removed_chunks = self.store.remove_pages(ids) if self.store else 0
            for pid in ids:
                self.pages.pop(pid, None)
            return (len(ids), removed_chunks)

    def delete_by_source(self, source: str) -> tuple[int, int]:
        ids = [pid for pid, p in self.pages.items() if p.source == source]
        return self.delete_pages(ids)

    def clear(self, base_dir: str) -> None:
        import shutil

        self.reset()
        shutil.rmtree(base_dir, ignore_errors=True)

    # ---- query ----
    def search(self, query: str, top_k: int):
        if not self.ready:
            return []
        qv = embeddings.embed_one(query, self.meta.embedding_model)
        return self.store.search(qv, top_k)

    def related(self, page_id: str, top_k: int = 5):
        """Pages most similar to the given page (excludes the page itself)."""
        page = self.pages.get(page_id)
        if not page or not self.ready:
            return []
        qv = embeddings.embed_one(f"{page.title}\n\n{page.text[:2000]}", self.meta.embedding_model)
        hits = self.store.search(qv, top_k * 4)
        seen: set[str] = set()
        out = []
        for score, rec in hits:
            if rec.page_id == page_id or rec.page_id in seen:
                continue
            seen.add(rec.page_id)
            p = self.pages.get(rec.page_id)
            if p:
                out.append((score, p))
            if len(out) >= top_k:
                break
        return out

    # ---- navigation ----
    def nav_tree(self) -> list[dict]:
        """Build an N-level tree from parent_url relationships."""
        children: dict[Optional[str], list[Page]] = {}
        url_to_page = {p.url: p for p in self.pages.values()}
        for p in self.pages.values():
            parent_id = None
            if p.parent_url and p.parent_url in url_to_page:
                parent_id = url_to_page[p.parent_url].page_id
            children.setdefault(parent_id, []).append(p)

        for bucket in children.values():
            bucket.sort(key=lambda x: (x.depth, x.title.lower()))

        def build(parent_id: Optional[str]) -> list[dict]:
            nodes = []
            for p in children.get(parent_id, []):
                nodes.append(
                    {
                        "page_id": p.page_id,
                        "title": p.title,
                        "url": p.url,
                        "depth": p.depth,
                        "children": build(p.page_id),
                    }
                )
            return nodes

        roots = build(None)
        # Fallback: if nothing is rooted (parents missing), expose shallowest pages.
        if not roots:
            roots = [
                {"page_id": p.page_id, "title": p.title, "url": p.url, "depth": p.depth, "children": []}
                for p in sorted(self.pages.values(), key=lambda x: (x.depth, x.title.lower()))
            ]
        return roots

    def breadcrumbs(self, page_id: str) -> list[dict]:
        url_to_page = {p.url: p for p in self.pages.values()}
        trail: list[dict] = []
        current = self.pages.get(page_id)
        guard = 0
        while current and guard < 20:
            trail.append({"title": current.title, "url": current.url, "page_id": current.page_id})
            if current.parent_url and current.parent_url in url_to_page:
                current = url_to_page[current.parent_url]
            else:
                break
            guard += 1
        return list(reversed(trail))

    # ---- persistence ----
    def save(self, base_dir: str) -> None:
        os.makedirs(base_dir, exist_ok=True)
        with open(os.path.join(base_dir, "pages.json"), "w", encoding="utf-8") as f:
            json.dump(
                {"meta": asdict(self.meta), "pages": [asdict(p) for p in self.pages.values()]},
                f,
                ensure_ascii=False,
            )
        if self.store:
            self.store.save(os.path.join(base_dir, "vectors"))

    def load(self, base_dir: str) -> bool:
        pages_path = os.path.join(base_dir, "pages.json")
        vectors_dir = os.path.join(base_dir, "vectors")
        if not (os.path.exists(pages_path) and VectorStore.exists(vectors_dir)):
            return False
        with open(pages_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        pages = {p["page_id"]: Page(**p) for p in data["pages"]}
        meta = KBMeta(**data["meta"])
        store = VectorStore.load(vectors_dir)
        self.set(pages, store, meta)
        return True


# Module-level singleton.
_kb: Optional[KnowledgeBase] = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
        base_dir = os.path.join(get_settings().data_dir, "kb")
        try:
            _kb.load(base_dir)
        except Exception:
            pass
    return _kb


def domain_of(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc

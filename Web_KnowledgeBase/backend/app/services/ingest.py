"""Orchestrates crawl -> chunk -> embed -> FAISS index -> persist, with job tracking."""
from __future__ import annotations

import os
import threading
import uuid

from ..config import get_settings
from ..crawler.crawler import Crawler
from ..extractors import extract_file
from ..models import JobStatus
from ..rag import embeddings
from ..rag.chunker import chunk_text
from ..rag.knowledge_base import KBMeta, KnowledgeBase, Page, domain_of, get_kb, page_id_for
from ..rag.vectorstore import ChunkRecord, VectorStore

# In-memory job registry (single-process). Swap for Redis in a multi-worker deploy.
_jobs: dict[str, JobStatus] = {}
_jobs_lock = threading.Lock()


def get_job(job_id: str) -> JobStatus | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def _set(job: JobStatus, **changes) -> None:
    with _jobs_lock:
        for k, v in changes.items():
            setattr(job, k, v)


def start_ingest(url: str, max_depth: int | None, max_pages: int | None, same_domain_only: bool | None) -> str:
    settings = get_settings()
    job = JobStatus(job_id=uuid.uuid4().hex[:12], state="queued", seed_url=url, domain=domain_of(url))
    with _jobs_lock:
        _jobs[job.job_id] = job

    depth = settings.max_crawl_depth if max_depth is None else max_depth
    pages = settings.max_pages if max_pages is None else max_pages
    same_domain = settings.same_domain_only if same_domain_only is None else same_domain_only

    thread = threading.Thread(
        target=_run, args=(job, url, depth, pages, same_domain), daemon=True
    )
    thread.start()
    return job.job_id


def _run(job: JobStatus, url: str, depth: int, max_pages: int, same_domain: bool) -> None:
    import asyncio

    settings = get_settings()
    try:
        _set(job, state="crawling", message="Crawling the portal…")

        crawler = Crawler(
            max_depth=depth,
            max_pages=max_pages,
            concurrency=settings.crawl_concurrency,
            timeout=settings.request_timeout,
            user_agent=settings.user_agent,
            same_domain_only=same_domain,
            respect_robots=settings.respect_robots,
        )

        async def on_page(_page):
            _set(job, pages_crawled=job.pages_crawled + 1)

        crawled = asyncio.run(crawler.crawl(url, on_page=on_page))
        if not crawled:
            _set(job, state="error", error="No pages could be crawled from the seed URL.", message="Crawl failed.")
            return

        _set(job, state="indexing", message="Embedding and indexing content…", pages_crawled=len(crawled))

        pages: dict[str, Page] = {}
        chunk_texts: list[str] = []
        chunk_records: list[ChunkRecord] = []

        for cp in crawled:
            pid = page_id_for(cp.url)
            page = Page(
                page_id=pid,
                url=cp.url,
                title=cp.title or cp.url,
                text=cp.text,
                depth=cp.depth,
                parent_url=cp.parent_url,
                headings=cp.headings,
            )
            pages[pid] = page

            for ch in chunk_text(cp.text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap):
                chunk_texts.append(ch.text)
                chunk_records.append(
                    ChunkRecord(
                        page_id=pid,
                        chunk_id=f"{pid}-{ch.index}",
                        url=cp.url,
                        title=page.title,
                        text=ch.text,
                    )
                )

        if not chunk_texts:
            _set(job, state="error", error="Crawled pages contained no indexable text.", message="Indexing failed.")
            return

        dim = embeddings.dimension(settings.embedding_model)
        store = VectorStore(dim=dim)
        # Embed in batches to keep memory bounded and report progress.
        batch = 256
        for i in range(0, len(chunk_texts), batch):
            sub_texts = chunk_texts[i : i + batch]
            sub_records = chunk_records[i : i + batch]
            vecs = embeddings.embed(sub_texts, settings.embedding_model)
            store.add(vecs, sub_records)
            _set(job, chunks_indexed=store.size)

        meta = KBMeta(
            seed_url=url,
            domain=domain_of(url),
            max_depth=max(p.depth for p in pages.values()),
            embedding_model=settings.embedding_model,
        )

        kb: KnowledgeBase = get_kb()
        kb.set(pages, store, meta)
        kb.save(os.path.join(settings.data_dir, "kb"))

        _set(
            job,
            state="done",
            message="Knowledge base ready.",
            pages_indexed=len(pages),
            chunks_indexed=store.size,
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        _set(job, state="error", error=str(exc), message="Ingestion failed.")


# ----------------------------------------------------------------- file uploads
def start_file_ingest(
    items: list[tuple[str, str | None, bytes]],
    append: bool,
    start_page: int | None = None,
    end_page: int | None = None,
) -> str:
    """items: list of (filename, content_type, data). Returns a job id."""
    job = JobStatus(job_id=uuid.uuid4().hex[:12], state="queued", seed_url="uploaded files", domain="uploads")
    with _jobs_lock:
        _jobs[job.job_id] = job
    thread = threading.Thread(target=_run_files, args=(job, items, append, start_page, end_page), daemon=True)
    thread.start()
    return job.job_id


def _run_files(
    job: JobStatus,
    items: list[tuple[str, str | None, bytes]],
    append: bool,
    start_page: int | None = None,
    end_page: int | None = None,
) -> None:
    settings = get_settings()
    try:
        _set(job, state="indexing", message="Extracting text from files…")
        kb: KnowledgeBase = get_kb()
        model = settings.embedding_model
        appending = append and kb.ready and kb.meta.embedding_model == model

        pages: dict[str, Page] = {}
        chunk_texts: list[str] = []
        chunk_records: list[ChunkRecord] = []
        skipped: list[str] = []

        for filename, ctype, data in items:
            try:
                doc = extract_file(filename, ctype, data, start_page=start_page, end_page=end_page)
            except Exception as exc:  # noqa: BLE001
                skipped.append(f"{filename}: {exc}")
                continue
            if not doc.text.strip():
                skipped.append(f"{filename}: no extractable text")
                continue

            url = f"upload://{filename}"
            pid = page_id_for(url)
            page = Page(
                page_id=pid,
                url=url,
                title=doc.title or filename,
                text=doc.text,
                depth=0,
                parent_url=None,
                headings=[],
                source="file",
            )
            pages[pid] = page
            _set(job, pages_crawled=len(pages))

            for ch in chunk_text(doc.text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap):
                chunk_texts.append(ch.text)
                chunk_records.append(
                    ChunkRecord(
                        page_id=pid,
                        chunk_id=f"{pid}-{ch.index}",
                        url=url,
                        title=page.title,
                        text=ch.text,
                    )
                )

        if not chunk_texts:
            detail = "; ".join(skipped) if skipped else "no files provided"
            _set(job, state="error", error=f"No indexable content. {detail}", message="Indexing failed.")
            return

        # Build vectors in batches.
        import numpy as np

        vec_batches = []
        batch = 256
        for i in range(0, len(chunk_texts), batch):
            vec_batches.append(embeddings.embed(chunk_texts[i : i + batch], model))
            _set(job, chunks_indexed=sum(len(v) for v in vec_batches))
        vectors = np.vstack(vec_batches)

        if appending:
            kb.add(pages, vectors, chunk_records)
            if not kb.meta.embedding_model:
                kb.meta.embedding_model = model
        else:
            kb.reset()
            store = VectorStore(dim=int(vectors.shape[1]))
            store.add(vectors, chunk_records)
            meta = KBMeta(seed_url="uploaded files", domain="uploads", max_depth=0, embedding_model=model)
            kb.set(pages, store, meta)

        kb.save(os.path.join(settings.data_dir, "kb"))

        msg = "Files indexed."
        if skipped:
            msg += f" Skipped {len(skipped)}: " + "; ".join(skipped[:5])
        _set(
            job,
            state="done",
            message=msg,
            pages_crawled=len(pages),
            pages_indexed=len(kb.pages),
            chunks_indexed=kb.store.size if kb.store else 0,
        )
    except Exception as exc:  # noqa: BLE001
        _set(job, state="error", error=str(exc), message="File ingestion failed.")

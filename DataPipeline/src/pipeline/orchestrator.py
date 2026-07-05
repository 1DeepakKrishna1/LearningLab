"""LangGraph-based pipeline orchestrator.

Each pipeline stage is a LangGraph node. The state flows through:
  ingest → extract → process → embed → enrich → store

Conditional edges handle errors gracefully without stopping the whole batch.
"""

from __future__ import annotations

import time
from typing import Any

from langgraph.graph import END, StateGraph

from src.embedding.embedder import Embedder
from src.embedding.vector_store import FAISSVectorStore
from src.enrichment.faq_generator import FAQGenerator
from src.enrichment.groq_client import GroqClient
from src.enrichment.knowledge_graph import KnowledgeGraphGenerator
from src.enrichment.question_generator import DOKQuestionGenerator
from src.extraction.pdf_processor import PDFProcessor
from src.ingestion.deduplicator import Deduplicator
from src.ingestion.local import LocalIngester
from src.models.schemas import (
    DocumentSource,
    PipelineState,
    PipelineStatus,
    ProcessedDocument,
)
from src.processing.chunker import SemanticChunker
from src.processing.cleaner import TextCleaner
from src.processing.metadata_extractor import MetadataExtractor
from src.storage.file_store import FileStore
from src.utils.logger import get_logger
from src.utils.metrics import PipelineMetrics
from src.utils.security import SecureConfig

logger = get_logger(__name__)


# ── Node implementations ──────────────────────────────────────────────────────

def _node_extract(state: dict[str, Any], processor: PDFProcessor, store: FileStore) -> dict:
    ps = PipelineState(**state)
    if ps.status == PipelineStatus.FAILED:
        return state

    t0 = time.perf_counter()
    try:
        if store.exists("extracted", ps.doc_id):
            data = store.load("extracted", ps.doc_id)
            from src.models.schemas import ExtractedContent
            ps.extracted_content = ExtractedContent(**data)
            logger.info("extraction_cache_hit", doc_id=ps.doc_id)
        else:
            ps.extracted_content = processor.process(
                ps.source_path, ps.doc_id, ps.file_name
            )
            store.save("extracted", ps.doc_id, ps.extracted_content)
        ps.status = PipelineStatus.EXTRACTED
    except Exception as exc:
        ps.mark_failed("extraction", str(exc))
        logger.error("extraction_failed", doc_id=ps.doc_id, error=str(exc))

    ps.stage_timings["extraction"] = round(time.perf_counter() - t0, 3)
    return ps.model_dump()


def _node_process(
    state: dict[str, Any],
    cleaner: TextCleaner,
    chunker: SemanticChunker,
    meta_extractor: MetadataExtractor,
    store: FileStore,
    metrics: PipelineMetrics,
) -> dict:
    ps = PipelineState(**state)
    if ps.status == PipelineStatus.FAILED or not ps.extracted_content:
        return state

    t0 = time.perf_counter()
    try:
        if store.exists("processed", ps.doc_id):
            data = store.load("processed", ps.doc_id)
            ps.processed_document = ProcessedDocument(**data)
            logger.info("processing_cache_hit", doc_id=ps.doc_id)
        else:
            ec = ps.extracted_content
            clean_text = cleaner.clean(ec.raw_text)
            chunks = chunker.chunk(clean_text, ps.doc_id)
            metadata = meta_extractor.extract(clean_text, ec.pdf_metadata, ec.total_pages)

            ps.processed_document = ProcessedDocument(
                doc_id=ps.doc_id,
                chunks=chunks,
                metadata=metadata,
            )
            store.save("processed", ps.doc_id, ps.processed_document)
            metrics.record_chunks(len(chunks))

        ps.status = PipelineStatus.PROCESSED
    except Exception as exc:
        ps.mark_failed("processing", str(exc))
        logger.error("processing_failed", doc_id=ps.doc_id, error=str(exc))

    ps.stage_timings["processing"] = round(time.perf_counter() - t0, 3)
    return ps.model_dump()


def _node_embed(
    state: dict[str, Any],
    embedder: Embedder,
    vector_store: FAISSVectorStore,
    store: FileStore,
) -> dict:
    ps = PipelineState(**state)
    if ps.status == PipelineStatus.FAILED or not ps.processed_document:
        return state

    t0 = time.perf_counter()
    try:
        if store.exists("embeddings", ps.doc_id):
            logger.info("embeddings_cache_hit", doc_id=ps.doc_id)
            raw = store.load("embeddings", ps.doc_id)
            from src.models.schemas import EmbeddingRecord
            ps.embeddings = [EmbeddingRecord(**r) for r in raw]
        else:
            ps.embeddings = embedder.embed_chunks(ps.processed_document.chunks)
            vector_store.add(ps.embeddings)
            store.save("embeddings", ps.doc_id, ps.embeddings)
        ps.status = PipelineStatus.EMBEDDED
    except Exception as exc:
        ps.mark_failed("embedding", str(exc))
        logger.error("embedding_failed", doc_id=ps.doc_id, error=str(exc))

    ps.stage_timings["embedding"] = round(time.perf_counter() - t0, 3)
    return ps.model_dump()


def _node_enrich_kg(
    state: dict[str, Any], kg_gen: KnowledgeGraphGenerator, store: FileStore
) -> dict:
    ps = PipelineState(**state)
    if ps.status == PipelineStatus.FAILED or not ps.processed_document:
        return state

    t0 = time.perf_counter()
    try:
        if store.exists("knowledge_graph", ps.doc_id):
            from src.models.schemas import KnowledgeGraph
            ps.knowledge_graph = KnowledgeGraph(**store.load("knowledge_graph", ps.doc_id))
        else:
            md = ps.processed_document.metadata
            ps.knowledge_graph = kg_gen.generate(
                chunks=ps.processed_document.chunks,
                doc_id=ps.doc_id,
                doc_title=md.title or ps.file_name,
                topics=md.topics,
            )
            store.save("knowledge_graph", ps.doc_id, ps.knowledge_graph)
    except Exception as exc:
        ps.add_error("knowledge_graph", str(exc))
        logger.error("kg_generation_failed", doc_id=ps.doc_id, error=str(exc))

    ps.stage_timings["knowledge_graph"] = round(time.perf_counter() - t0, 3)
    return ps.model_dump()


def _node_enrich_faq(
    state: dict[str, Any], faq_gen: FAQGenerator, store: FileStore
) -> dict:
    ps = PipelineState(**state)
    if ps.status == PipelineStatus.FAILED or not ps.processed_document:
        return state

    t0 = time.perf_counter()
    try:
        if store.exists("faq", ps.doc_id):
            from src.models.schemas import FAQPair
            raw = store.load("faq", ps.doc_id)
            ps.faqs = [FAQPair(**f) for f in raw]
        else:
            md = ps.processed_document.metadata
            ps.faqs = faq_gen.generate(
                chunks=ps.processed_document.chunks,
                doc_id=ps.doc_id,
                doc_title=md.title or ps.file_name,
                topics=md.topics,
                keywords=md.keywords,
            )
            store.save("faq", ps.doc_id, ps.faqs)
    except Exception as exc:
        ps.add_error("faq", str(exc))
        logger.error("faq_generation_failed", doc_id=ps.doc_id, error=str(exc))

    ps.stage_timings["faq"] = round(time.perf_counter() - t0, 3)
    return ps.model_dump()


def _node_enrich_questions(
    state: dict[str, Any], q_gen: DOKQuestionGenerator, store: FileStore
) -> dict:
    ps = PipelineState(**state)
    if ps.status == PipelineStatus.FAILED or not ps.processed_document:
        return state

    t0 = time.perf_counter()
    try:
        if store.exists("questions", ps.doc_id):
            from src.models.schemas import DOKQuestions
            ps.dok_questions = DOKQuestions(**store.load("questions", ps.doc_id))
        else:
            md = ps.processed_document.metadata
            ps.dok_questions = q_gen.generate(
                chunks=ps.processed_document.chunks,
                doc_id=ps.doc_id,
                doc_title=md.title or ps.file_name,
                topics=md.topics,
            )
            store.save("questions", ps.doc_id, ps.dok_questions)
    except Exception as exc:
        ps.add_error("questions", str(exc))
        logger.error("questions_generation_failed", doc_id=ps.doc_id, error=str(exc))

    ps.stage_timings["questions"] = round(time.perf_counter() - t0, 3)
    return ps.model_dump()


def _node_finalise(state: dict[str, Any], store: FileStore) -> dict:
    ps = PipelineState(**state)
    if ps.status != PipelineStatus.FAILED:
        ps.status = PipelineStatus.COMPLETED
        store.mark_completed(ps.doc_id)
        logger.info(
            "pipeline_completed",
            doc_id=ps.doc_id,
            timings=ps.stage_timings,
            errors=ps.errors,
        )
    else:
        store.mark_failed(ps.doc_id, "; ".join(ps.errors))
    return ps.model_dump()


def _route_after_extract(state: dict[str, Any]) -> str:
    return "failed" if state.get("status") == PipelineStatus.FAILED else "process"


def _route_after_process(state: dict[str, Any]) -> str:
    return "failed" if state.get("status") == PipelineStatus.FAILED else "embed"


def _route_after_embed(state: dict[str, Any]) -> str:
    return "failed" if state.get("status") == PipelineStatus.FAILED else "enrich_kg"


# ── Orchestrator ──────────────────────────────────────────────────────────────

class PipelineOrchestrator:
    """Assembles and runs the LangGraph pipeline for a single document."""

    def __init__(self, config: SecureConfig) -> None:
        self.config = config
        cfg = config

        self.metrics = PipelineMetrics(
            enable_server=cfg.settings.enable_metrics,
            port=cfg.settings.metrics_port,
        )
        self.store = FileStore(cfg.settings.output_dir)
        self.dedup = Deduplicator(f"{cfg.settings.output_dir}/.dedup_index.json")

        # Extraction
        ext_cfg = cfg.get("extraction", default={})
        self.processor = PDFProcessor(
            output_dir=cfg.settings.output_dir,
            text_backend=ext_cfg.get("text", {}).get("backend", "pymupdf"),
            table_backend=ext_cfg.get("tables", {}).get("backend", "pdfplumber"),
            ocr_enabled=ext_cfg.get("images", {}).get("ocr", {}).get("enabled", True),
            metrics=self.metrics,
        )

        # Processing
        proc_cfg = cfg.get("processing", default={})
        chunk_cfg = proc_cfg.get("chunking", {})
        self.cleaner = TextCleaner()
        self.chunker = SemanticChunker(
            strategy=chunk_cfg.get("strategy", "semantic"),
            chunk_size=chunk_cfg.get("chunk_size", 512),
            chunk_overlap=chunk_cfg.get("chunk_overlap", 64),
            min_chunk_size=chunk_cfg.get("min_chunk_size", 50),
        )
        meta_cfg = proc_cfg.get("metadata", {})
        self.meta_extractor = MetadataExtractor(
            ner_model=meta_cfg.get("ner_model", "en_core_web_sm"),
            max_keywords=meta_cfg.get("max_keywords", 15),
        )

        # Embedding
        emb_cfg = cfg.get("embedding", default={})
        self.embedder = Embedder(
            model_name=cfg.settings.embedding_model,
            device=cfg.settings.embedding_device,
            batch_size=emb_cfg.get("batch_size", 64),
            normalize=emb_cfg.get("normalize", True),
            metrics=self.metrics,
        )
        self.vector_store = FAISSVectorStore(
            save_path=emb_cfg.get("vector_store", {}).get("save_path", "./output/embeddings"),
            dimensions=384,
        )

        # Enrichment
        self.groq = GroqClient(config=cfg, metrics=self.metrics)
        enr_cfg = cfg.get("enrichment", default={})
        self.kg_gen = KnowledgeGraphGenerator(self.groq)
        self.faq_gen = FAQGenerator(
            self.groq,
            pairs_per_chunk=enr_cfg.get("faq", {}).get("pairs_per_chunk", 5),
        )
        self.q_gen = DOKQuestionGenerator(
            self.groq,
            questions_per_level=enr_cfg.get("questions", {}).get("questions_per_level", 3),
        )

        self._graph = self._build_graph()

    def _build_graph(self):
        """Construct and compile the LangGraph state machine."""
        graph = StateGraph(dict)

        # Bind dependencies into node functions via closures
        graph.add_node("extract", lambda s: _node_extract(s, self.processor, self.store))
        graph.add_node("process", lambda s: _node_process(s, self.cleaner, self.chunker, self.meta_extractor, self.store, self.metrics))
        graph.add_node("embed", lambda s: _node_embed(s, self.embedder, self.vector_store, self.store))
        graph.add_node("enrich_kg", lambda s: _node_enrich_kg(s, self.kg_gen, self.store))
        graph.add_node("enrich_faq", lambda s: _node_enrich_faq(s, self.faq_gen, self.store))
        graph.add_node("enrich_questions", lambda s: _node_enrich_questions(s, self.q_gen, self.store))
        graph.add_node("finalise", lambda s: _node_finalise(s, self.store))
        graph.add_node("failed", lambda s: _node_finalise(s, self.store))

        graph.set_entry_point("extract")

        graph.add_conditional_edges("extract", _route_after_extract, {"process": "process", "failed": "failed"})
        graph.add_conditional_edges("process", _route_after_process, {"embed": "embed", "failed": "failed"})
        graph.add_conditional_edges("embed", _route_after_embed, {"enrich_kg": "enrich_kg", "failed": "failed"})
        graph.add_edge("enrich_kg", "enrich_faq")
        graph.add_edge("enrich_faq", "enrich_questions")
        graph.add_edge("enrich_questions", "finalise")
        graph.add_edge("finalise", END)
        graph.add_edge("failed", END)

        return graph.compile()

    def run(self, source: DocumentSource) -> PipelineState:
        """Run the full pipeline for a single document source."""
        # Quick ingestion step (outside graph for flexibility)
        local_ingester = LocalIngester(
            input_dir=self.config.settings.input_dir,
            file_store=self.store,
            deduplicator=self.dedup,
            metrics=self.metrics,
        )

        raw_doc = local_ingester.ingest(source)
        if raw_doc is None:
            logger.info("document_skipped_duplicate", file=source.file_name)
            return PipelineState(status=PipelineStatus.SKIPPED, file_name=source.file_name)

        # Check idempotency
        if self.store.is_completed(raw_doc.doc_id):
            logger.info("document_already_completed", doc_id=raw_doc.doc_id)
            return PipelineState(
                doc_id=raw_doc.doc_id,
                status=PipelineStatus.COMPLETED,
                file_name=source.file_name,
            )

        initial_state = PipelineState(
            doc_id=raw_doc.doc_id,
            source_path=raw_doc.local_path,
            source_type=source.source_type.value,
            file_name=source.file_name,
            raw_document=raw_doc,
            status=PipelineStatus.INGESTED,
        ).model_dump()

        result = self._graph.invoke(initial_state)
        return PipelineState(**result)

    def run_batch(self, sources: list[DocumentSource]) -> list[PipelineState]:
        """Process a list of document sources sequentially."""
        results: list[PipelineState] = []
        for i, source in enumerate(sources, start=1):
            logger.info("batch_progress", current=i, total=len(sources), file=source.file_name)
            result = self.run(source)
            results.append(result)
        return results

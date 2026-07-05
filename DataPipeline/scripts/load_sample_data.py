#!/usr/bin/env python3
"""Load sample data and run a demo pipeline pass.

Steps:
  1. Generate 3 realistic sample PDFs (ML paper, financial report, API guide)
  2. Copy them to the input directory
  3. Run the pipeline on each (extraction + processing + embedding + enrichment)
  4. Print a summary of outputs

Usage:
  python scripts/load_sample_data.py
  python scripts/load_sample_data.py --skip-enrich   # skip GroQ LLM calls
  python scripts/load_sample_data.py --input-dir ./my_pdfs
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))


def main(args: argparse.Namespace) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    console.print(Panel("[bold cyan]DataPipeline — Sample Data Loader[/bold cyan]", expand=False))

    # ── Step 1: Generate sample PDFs ────────────────────────────────────────
    console.print("\n[bold]Step 1:[/bold] Generating sample PDFs...")
    from scripts.create_sample_pdfs import create_pdfs
    sample_dir = Path(args.sample_dir)
    pdf_paths = create_pdfs(str(sample_dir))
    console.print(f"  [green]✓[/green] {len(pdf_paths)} PDFs created in {sample_dir}")

    # ── Step 2: Copy to input directory ─────────────────────────────────────
    input_dir = Path(args.input_dir)
    input_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"\n[bold]Step 2:[/bold] Copying PDFs to input directory ({input_dir})...")
    for pdf in pdf_paths:
        dest = input_dir / Path(pdf).name
        shutil.copy2(pdf, dest)
        console.print(f"  [green]✓[/green] {Path(pdf).name}")

    # ── Step 3: Configure and run pipeline ──────────────────────────────────
    console.print("\n[bold]Step 3:[/bold] Running pipeline...")

    from src.utils.logger import configure_logging
    from src.utils.security import get_config
    configure_logging(level="INFO", fmt="console")
    cfg = get_config("config/config.yaml")
    cfg.settings.input_dir = str(input_dir)

    if args.skip_enrich:
        console.print("  [yellow]⚠ Skipping AI enrichment (--skip-enrich flag)[/yellow]")

    from src.ingestion.local import LocalIngester
    from src.storage.file_store import FileStore
    from src.ingestion.deduplicator import Deduplicator
    from src.utils.metrics import PipelineMetrics
    from src.extraction.pdf_processor import PDFProcessor
    from src.processing.cleaner import TextCleaner
    from src.processing.chunker import SemanticChunker
    from src.processing.metadata_extractor import MetadataExtractor
    from src.embedding.embedder import Embedder
    from src.embedding.vector_store import FAISSVectorStore
    from src.models.schemas import PipelineStatus

    metrics = PipelineMetrics(enable_server=False)
    store = FileStore(cfg.settings.output_dir)
    dedup = Deduplicator(f"{cfg.settings.output_dir}/.dedup_index.json")
    ingester = LocalIngester(str(input_dir), store, dedup, metrics)

    processor = PDFProcessor(output_dir=cfg.settings.output_dir, ocr_enabled=False, metrics=metrics)
    cleaner = TextCleaner()
    chunker = SemanticChunker(chunk_size=512, chunk_overlap=64)
    meta_ex = MetadataExtractor()
    embedder = Embedder(model_name=cfg.settings.embedding_model, device="cpu", metrics=metrics)
    vs = FAISSVectorStore(
        save_path=f"{cfg.settings.output_dir}/embeddings",
        dimensions=384,
    )

    results = []
    for source in ingester.discover():
        console.print(f"\n  Processing: [cyan]{source.file_name}[/cyan]")
        raw_doc = ingester.ingest(source)
        if raw_doc is None:
            console.print("    [yellow]Skipped (duplicate)[/yellow]")
            results.append({"file": source.file_name, "status": "skipped"})
            continue

        t0 = time.perf_counter()
        try:
            # Extract
            extracted = processor.process(raw_doc.local_path, raw_doc.doc_id, source.file_name)
            store.save("extracted", raw_doc.doc_id, extracted)
            console.print(f"    [green]✓[/green] Extracted: {extracted.total_pages} pages, {len(extracted.tables)} tables")

            # Process
            clean_text = cleaner.clean(extracted.raw_text)
            chunks = chunker.chunk(clean_text, raw_doc.doc_id)
            metadata = meta_ex.extract(clean_text, extracted.pdf_metadata, extracted.total_pages)
            from src.models.schemas import ProcessedDocument
            processed = ProcessedDocument(doc_id=raw_doc.doc_id, chunks=chunks, metadata=metadata)
            store.save("processed", raw_doc.doc_id, processed)
            console.print(f"    [green]✓[/green] Processed: {len(chunks)} chunks, keywords: {metadata.keywords[:3]}")

            # Embed
            emb_records = embedder.embed_chunks(chunks)
            vs.add(emb_records)
            store.save("embeddings", raw_doc.doc_id, emb_records)
            console.print(f"    [green]✓[/green] Embedded: {len(emb_records)} vectors")

            # Enrichment (skip if flag set or no API key)
            if not args.skip_enrich:
                groq_key = ""
                try:
                    groq_key = cfg.get_groq_api_key()
                except ValueError:
                    pass

                if groq_key:
                    _run_enrichment(cfg, processed, raw_doc.doc_id, source.file_name, store, console)
                else:
                    console.print("    [yellow]⚠ GROQ_API_KEY not set — skipping AI enrichment[/yellow]")
                    _save_mock_enrichment(raw_doc.doc_id, store)
            else:
                _save_mock_enrichment(raw_doc.doc_id, store)

            store.mark_completed(raw_doc.doc_id)
            elapsed = time.perf_counter() - t0
            results.append({"file": source.file_name, "status": "completed", "seconds": round(elapsed, 1)})
            console.print(f"    [bold green]✓ Completed in {elapsed:.1f}s[/bold green]")

        except Exception as exc:
            store.mark_failed(raw_doc.doc_id, str(exc))
            results.append({"file": source.file_name, "status": "failed", "error": str(exc)})
            console.print(f"    [red]✗ Failed: {exc}[/red]")

    # ── Step 4: Print summary ────────────────────────────────────────────────
    console.print("\n[bold]Step 4:[/bold] Summary\n")
    t = Table("File", "Status", "Time (s)")
    for r in results:
        status_fmt = {
            "completed": "[green]completed[/green]",
            "failed": "[red]failed[/red]",
            "skipped": "[yellow]skipped[/yellow]",
        }.get(r["status"], r["status"])
        t.add_row(r["file"], status_fmt, str(r.get("seconds", "-")))
    console.print(t)

    console.print(f"\n[bold green]Output written to:[/bold green] {cfg.settings.output_dir}/")
    console.print("  • extracted/  — raw extracted content JSON")
    console.print("  • processed/  — chunks + metadata JSON")
    console.print("  • embeddings/ — FAISS index + metadata")
    console.print("  • knowledge_graph/ — entity/relationship graphs")
    console.print("  • faq/         — FAQ pairs")
    console.print("  • questions/   — DOK-level questions\n")


def _run_enrichment(cfg, processed, doc_id, file_name, store, console) -> None:
    from src.enrichment.groq_client import GroqClient
    from src.enrichment.knowledge_graph import KnowledgeGraphGenerator
    from src.enrichment.faq_generator import FAQGenerator
    from src.enrichment.question_generator import DOKQuestionGenerator

    groq = GroqClient(config=cfg)
    md = processed.metadata
    title = md.title or file_name

    # Use only first 3 chunks to limit API calls in demo
    demo_chunks = processed.chunks[:3]

    kg_gen = KnowledgeGraphGenerator(groq)
    kg = kg_gen.generate(demo_chunks, doc_id, title, md.topics)
    store.save("knowledge_graph", doc_id, kg)
    console.print(f"    [green]✓[/green] Knowledge graph: {len(kg.entities)} entities")

    faq_gen = FAQGenerator(groq, pairs_per_chunk=3)
    faqs = faq_gen.generate(demo_chunks, doc_id, title, md.topics, md.keywords)
    store.save("faq", doc_id, faqs)
    console.print(f"    [green]✓[/green] FAQs: {len(faqs)} pairs")

    q_gen = DOKQuestionGenerator(groq, questions_per_level=2)
    questions = q_gen.generate(demo_chunks, doc_id, title, md.topics)
    store.save("questions", doc_id, questions)
    total_qs = sum([len(questions.level_1), len(questions.level_2), len(questions.level_3), len(questions.level_4)])
    console.print(f"    [green]✓[/green] DOK questions: {total_qs} total")


def _save_mock_enrichment(doc_id: str, store) -> None:
    """Save placeholder enrichment outputs when GroQ is not available."""
    from src.models.schemas import KnowledgeGraph, DOKQuestions

    store.save("knowledge_graph", doc_id, KnowledgeGraph(doc_id=doc_id))
    store.save("faq", doc_id, [])
    store.save("questions", doc_id, DOKQuestions(doc_id=doc_id))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load sample data into the DataPipeline")
    parser.add_argument("--input-dir", default="./input", help="Input directory for PDFs")
    parser.add_argument("--sample-dir", default="./sample_data/samples", help="Where to generate sample PDFs")
    parser.add_argument("--skip-enrich", action="store_true", help="Skip GroQ LLM enrichment")
    args = parser.parse_args()
    main(args)

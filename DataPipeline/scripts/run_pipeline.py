#!/usr/bin/env python3
"""CLI entrypoint for the DataPipeline.

Usage examples:
  python scripts/run_pipeline.py run --input ./input
  python scripts/run_pipeline.py run --input ./input --source gdrive
  python scripts/run_pipeline.py status
  python scripts/run_pipeline.py search --query "machine learning"
"""

import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from src.utils.logger import configure_logging
from src.utils.security import get_config

console = Console()


@click.group()
@click.option("--config", default="config/config.yaml", help="Path to config file")
@click.option("--log-level", default="INFO", help="Logging level")
@click.pass_context
def cli(ctx: click.Context, config: str, log_level: str) -> None:
    """DataPipeline — Production PDF processing and AI enrichment pipeline."""
    ctx.ensure_object(dict)
    cfg = get_config(config)
    configure_logging(level=log_level, fmt=cfg.settings.log_format)
    ctx.obj["config"] = cfg


@cli.command()
@click.option("--input", "input_dir", default=None, help="Input directory (overrides config)")
@click.option("--source", default="local", type=click.Choice(["local", "gdrive", "sharepoint"]))
@click.option("--dry-run", is_flag=True, help="Discover files only, do not process")
@click.pass_context
def run(ctx: click.Context, input_dir: str, source: str, dry_run: bool) -> None:
    """Ingest and process all PDFs from the specified source."""
    from src.pipeline.orchestrator import PipelineOrchestrator
    from src.models.schemas import PipelineStatus

    cfg = ctx.obj["config"]
    if input_dir:
        cfg.settings.input_dir = input_dir

    orchestrator = PipelineOrchestrator(cfg)

    if source == "local":
        from src.ingestion.local import LocalIngester
        ingester = LocalIngester(
            input_dir=cfg.settings.input_dir,
            file_store=orchestrator.store,
            deduplicator=orchestrator.dedup,
            metrics=orchestrator.metrics,
        )
        sources = list(ingester.discover())
    elif source == "gdrive":
        from src.ingestion.gdrive import GDriveIngester
        ingester = GDriveIngester(cfg, orchestrator.store, orchestrator.dedup, orchestrator.metrics)
        sources = list(ingester.discover())
    elif source == "sharepoint":
        from src.ingestion.sharepoint import SharePointIngester
        ingester = SharePointIngester(cfg, orchestrator.store, orchestrator.dedup, orchestrator.metrics)
        sources = list(ingester.discover())
    else:
        console.print(f"[red]Unknown source: {source}[/red]")
        return

    if not sources:
        console.print("[yellow]No PDFs found in the specified source.[/yellow]")
        return

    console.print(f"\n[bold green]Found {len(sources)} PDF(s) to process[/bold green]\n")

    if dry_run:
        t = Table("File", "Size (KB)", "Source")
        for s in sources:
            t.add_row(s.file_name, f"{s.file_size_bytes // 1024}", s.source_type.value)
        console.print(t)
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=len(sources))
        results = []
        for src in sources:
            progress.update(task, description=f"Processing {src.file_name}")
            result = orchestrator.run(src)
            results.append(result)
            progress.advance(task)

    _print_summary(results)


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show pipeline processing status for all documents."""
    from src.storage.file_store import FileStore
    cfg = ctx.obj["config"]
    store = FileStore(cfg.settings.output_dir)

    completed = store.list_completed()
    failed = store.list_failed()

    console.print(f"\n[green]Completed:[/green] {len(completed)}")
    console.print(f"[red]Failed:[/red] {len(failed)}\n")

    if failed:
        console.print("[bold red]Failed documents:[/bold red]")
        for doc_id in failed:
            state = store.get_doc_state(doc_id)
            errors = state.get("errors", [])
            console.print(f"  {doc_id[:12]}... — {errors[-1]['error'] if errors else 'unknown'}")


@cli.command()
@click.option("--query", required=True, help="Search query")
@click.option("--top-k", default=5, help="Number of results to return")
@click.pass_context
def search(ctx: click.Context, query: str, top_k: int) -> None:
    """Semantic search across all embedded document chunks."""
    from src.embedding.embedder import Embedder
    from src.embedding.vector_store import FAISSVectorStore
    cfg = ctx.obj["config"]

    embedder = Embedder(model_name=cfg.settings.embedding_model)
    vs = FAISSVectorStore(
        save_path=f"{cfg.settings.output_dir}/embeddings",
        dimensions=embedder.dimensions,
    )

    if vs.total_vectors == 0:
        console.print("[yellow]Vector store is empty. Run the pipeline first.[/yellow]")
        return

    query_vec = embedder.embed_query(query)
    results = vs.search(query_vec, top_k=top_k)

    t = Table("Rank", "Chunk ID", "Doc ID", "Distance")
    for i, r in enumerate(results, start=1):
        t.add_row(str(i), r["chunk_id"][:12], r["doc_id"][:12], f"{r['distance']:.4f}")
    console.print(t)


def _print_summary(results: list) -> None:
    from src.models.schemas import PipelineStatus
    completed = sum(1 for r in results if r.status == PipelineStatus.COMPLETED)
    failed = sum(1 for r in results if r.status == PipelineStatus.FAILED)
    skipped = sum(1 for r in results if r.status == PipelineStatus.SKIPPED)

    console.print("\n[bold]── Pipeline Summary ──[/bold]")
    console.print(f"  [green]Completed:[/green] {completed}")
    console.print(f"  [yellow]Skipped (duplicate):[/yellow] {skipped}")
    console.print(f"  [red]Failed:[/red] {failed}")

    if failed:
        console.print("\n[bold red]Failures:[/bold red]")
        for r in results:
            if r.status == PipelineStatus.FAILED:
                console.print(f"  {r.file_name}: {'; '.join(r.errors)}")


if __name__ == "__main__":
    cli()

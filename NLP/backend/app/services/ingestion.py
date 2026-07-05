"""
Data ingestion service.

Responsibilities:
  - Save uploaded file to disk (./uploads/{dataset_id}/original.{ext})
  - Detect file encoding with chardet
  - Read CSV / XLS / XLSX in 10 000-row chunks using pandas
  - Create a per-dataset SQLite table named  data_{uuid_no_hyphens}
  - Insert rows in batches
  - Update dataset status throughout: pending → processing → ready | error
"""
from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
import chardet
import pandas as pd
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import ProcessingError
from app.database import execute_dataset_query
from app.models.dataset import Dataset, DatasetColumn

settings = get_settings()

SUPPORTED_TYPES = {"csv", "xlsx", "xls"}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _table_name(dataset_id: str) -> str:
    return "data_" + dataset_id.replace("-", "")


def _safe_column_name(name: str) -> str:
    """Normalise a column name so it is a valid SQLite identifier."""
    import re
    name = str(name).strip()
    name = re.sub(r"[^\w]", "_", name)
    if name and name[0].isdigit():
        name = "col_" + name
    return name or "col"


async def _read_file_bytes(file_path: str) -> bytes:
    async with aiofiles.open(file_path, "rb") as f:
        return await f.read()


def _detect_encoding(raw: bytes) -> str:
    result = chardet.detect(raw[:100_000])  # sample first 100 KB
    return result.get("encoding") or "utf-8"


def _iter_chunks(
    raw: bytes,
    file_type: str,
    encoding: str,
    chunk_size: int,
) -> list[pd.DataFrame]:
    """Return a list of DataFrame chunks regardless of file type."""
    if file_type == "csv":
        chunks = []
        for chunk in pd.read_csv(
            io.BytesIO(raw),
            encoding=encoding,
            chunksize=chunk_size,
            low_memory=False,
            on_bad_lines="skip",
        ):
            chunks.append(chunk)
        return chunks
    elif file_type in ("xlsx", "xls"):
        engine = "openpyxl" if file_type == "xlsx" else "xlrd"
        df = pd.read_excel(io.BytesIO(raw), engine=engine)
        return [df[i : i + chunk_size] for i in range(0, len(df), chunk_size)]
    else:
        raise ProcessingError(f"Unsupported file type: {file_type}")


async def _create_dataset_table(table_name: str, columns: list[str]) -> None:
    """Create (or drop+recreate) the SQLite table for this dataset."""
    import aiosqlite
    from app.database import _db_path

    col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" (id INTEGER PRIMARY KEY AUTOINCREMENT, {col_defs})'

    async with aiosqlite.connect(_db_path()) as conn:
        await conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        await conn.execute(create_sql)
        await conn.commit()


async def _insert_chunk(table_name: str, df: pd.DataFrame) -> None:
    """Insert a DataFrame chunk into the dataset table."""
    import aiosqlite
    from app.database import _db_path

    if df.empty:
        return

    cols = [f'"{c}"' for c in df.columns]
    placeholders = ", ".join("?" for _ in df.columns)
    insert_sql = f'INSERT INTO "{table_name}" ({", ".join(cols)}) VALUES ({placeholders})'

    # Convert all values to strings (preserves data without type headaches)
    rows = [
        tuple(None if pd.isna(v) else str(v) for v in row)
        for row in df.itertuples(index=False, name=None)
    ]

    async with aiosqlite.connect(_db_path()) as conn:
        await conn.executemany(insert_sql, rows)
        await conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Public service
# ─────────────────────────────────────────────────────────────────────────────

class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_upload(
        self,
        file_bytes: bytes,
        original_filename: str,
        dataset_name: str,
    ) -> Dataset:
        """
        Persist the uploaded file to disk, create the Dataset record,
        and return it (status = pending).
        """
        ext = Path(original_filename).suffix.lstrip(".").lower()
        if ext not in SUPPORTED_TYPES:
            raise ProcessingError(
                f"Unsupported file type: .{ext}",
                f"Allowed types: {', '.join(SUPPORTED_TYPES)}",
            )

        dataset_id = str(uuid.uuid4())
        table_name = _table_name(dataset_id)

        # ── Persist file ──────────────────────────────────────────────────────
        upload_dir = Path(settings.upload_dir) / dataset_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"original.{ext}"

        async with aiofiles.open(str(file_path), "wb") as f:
            await f.write(file_bytes)

        # ── Create DB record ──────────────────────────────────────────────────
        dataset = Dataset(
            id=dataset_id,
            name=dataset_name,
            original_filename=original_filename,
            file_path=str(file_path),
            file_size_bytes=len(file_bytes),
            file_type=ext,
            status="pending",
            table_name=table_name,
        )
        self.db.add(dataset)
        await self.db.flush()

        logger.info(
            "upload_saved",
            dataset_id=dataset_id,
            filename=original_filename,
            size_bytes=len(file_bytes),
        )
        return dataset

    async def process_dataset(self, dataset_id: str) -> None:
        """
        Full pipeline: read file → detect encoding → chunk-load →
        create SQLite table → insert rows → update metadata columns →
        mark ready.

        Designed to run as a BackgroundTask (no HTTP context).
        """
        from sqlalchemy import select, update
        from app.database import AsyncSessionLocal
        from app.services.metadata import MetadataService

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Dataset).where(Dataset.id == dataset_id)
            )
            dataset = result.scalar_one_or_none()
            if dataset is None:
                logger.error("process_dataset_not_found", dataset_id=dataset_id)
                return

            try:
                # ── Status → processing ───────────────────────────────────────
                dataset.status = "processing"
                await db.commit()

                logger.info("ingestion_started", dataset_id=dataset_id)

                # ── Read file ─────────────────────────────────────────────────
                raw = await _read_file_bytes(dataset.file_path)
                encoding = _detect_encoding(raw) if dataset.file_type == "csv" else "utf-8"
                logger.info("encoding_detected", dataset_id=dataset_id, encoding=encoding)

                chunks = _iter_chunks(
                    raw, dataset.file_type, encoding, settings.chunk_size
                )

                if not chunks:
                    raise ProcessingError("File produced no data chunks.")

                # Normalise column names using the first chunk
                first_df = chunks[0]
                norm_cols = [_safe_column_name(c) for c in first_df.columns]
                col_map = dict(zip(first_df.columns, norm_cols))

                # Rename all chunks
                chunks = [df.rename(columns=col_map) for df in chunks]

                # ── Create SQLite table ───────────────────────────────────────
                await _create_dataset_table(dataset.table_name, norm_cols)

                # ── Insert chunks ─────────────────────────────────────────────
                total_rows = 0
                for chunk in chunks:
                    await _insert_chunk(dataset.table_name, chunk)
                    total_rows += len(chunk)
                    logger.debug(
                        "chunk_inserted",
                        dataset_id=dataset_id,
                        rows_so_far=total_rows,
                    )

                # ── Compute metadata ──────────────────────────────────────────
                full_df = pd.concat(chunks, ignore_index=True)
                meta_svc = MetadataService(db)
                await meta_svc.generate_column_metadata(dataset_id, full_df)

                # ── Mark ready ────────────────────────────────────────────────
                dataset.status = "ready"
                dataset.row_count = total_rows
                dataset.column_count = len(norm_cols)
                await db.commit()

                logger.info(
                    "ingestion_complete",
                    dataset_id=dataset_id,
                    rows=total_rows,
                    columns=len(norm_cols),
                )

            except Exception as exc:
                logger.exception("ingestion_failed", dataset_id=dataset_id, error=str(exc))
                dataset.status = "error"
                dataset.error_message = str(exc)[:1000]
                await db.commit()

"""
Dataset API endpoints.

POST   /datasets/upload          — upload CSV/XLS/XLSX, trigger background processing
GET    /datasets                 — list all datasets
GET    /datasets/{id}            — get dataset details + column metadata
DELETE /datasets/{id}            — delete dataset + data table
GET    /datasets/{id}/columns    — list columns only
"""
from __future__ import annotations

import os
from typing import List

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AppError, DatasetNotFound, ProcessingError
from app.database import get_db
from app.models.dataset import Dataset
from app.schemas.dataset import DatasetColumnRead, DatasetListItem, DatasetRead
from app.services.ingestion import IngestionService, SUPPORTED_TYPES

router = APIRouter()
settings = get_settings()


def _app_error_to_http(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.to_dict())


@router.post("/upload", response_model=DatasetRead, status_code=status.HTTP_202_ACCEPTED)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> DatasetRead:
    """
    Upload a file (CSV / XLS / XLSX, max 100 MB).
    Returns immediately with status=pending; processing runs in background.
    Poll GET /datasets/{id} for status updates.
    """
    # Size check
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "File too large.",
                "detail": f"Maximum allowed size is {settings.max_file_size_mb} MB.",
                "code": "FILE_TOO_LARGE",
            },
        )

    # Extension check
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "error": f"Unsupported file type: .{ext}",
                "detail": f"Allowed: {', '.join(SUPPORTED_TYPES)}",
                "code": "UNSUPPORTED_FILE_TYPE",
            },
        )

    try:
        svc = IngestionService(db)
        dataset = await svc.save_upload(
            file_bytes=file_bytes,
            original_filename=file.filename or "upload",
            dataset_name=name.strip() or file.filename or "Unnamed dataset",
        )
        # Schedule background processing
        background_tasks.add_task(svc.process_dataset, dataset.id)

        logger.info(
            "dataset_upload_accepted",
            dataset_id=dataset.id,
            filename=file.filename,
            size=len(file_bytes),
        )
        return DatasetRead.model_validate(dataset)

    except AppError as exc:
        raise _app_error_to_http(exc)


@router.get("", response_model=List[DatasetListItem])
async def list_datasets(db: AsyncSession = Depends(get_db)) -> List[DatasetListItem]:
    """Return all datasets ordered by most-recently created first."""
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    datasets = result.scalars().all()
    return [DatasetListItem.model_validate(d) for d in datasets]


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> DatasetRead:
    """Get full dataset info including column metadata."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise _app_error_to_http(DatasetNotFound(dataset_id))
    return DatasetRead.model_validate(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete dataset record, column metadata, uploaded file, and data table."""
    import aiosqlite
    from app.database import _db_path

    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise _app_error_to_http(DatasetNotFound(dataset_id))

    # Drop SQLite data table
    if dataset.table_name:
        try:
            async with aiosqlite.connect(_db_path()) as conn:
                await conn.execute(f'DROP TABLE IF EXISTS "{dataset.table_name}"')
                await conn.commit()
        except Exception as exc:
            logger.warning("drop_table_failed", table=dataset.table_name, error=str(exc))

    # Remove uploaded file
    try:
        if os.path.exists(dataset.file_path):
            os.remove(dataset.file_path)
            # Remove parent dir if empty
            parent = os.path.dirname(dataset.file_path)
            if not os.listdir(parent):
                os.rmdir(parent)
    except Exception as exc:
        logger.warning("delete_file_failed", path=dataset.file_path, error=str(exc))

    await db.delete(dataset)
    logger.info("dataset_deleted", dataset_id=dataset_id)


@router.get("/{dataset_id}/columns", response_model=List[DatasetColumnRead])
async def list_columns(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[DatasetColumnRead]:
    """Return column metadata for a dataset."""
    from sqlalchemy import select as sa_select
    from app.models.dataset import DatasetColumn

    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    if not result.scalar_one_or_none():
        raise _app_error_to_http(DatasetNotFound(dataset_id))

    col_result = await db.execute(
        sa_select(DatasetColumn)
        .where(DatasetColumn.dataset_id == dataset_id)
        .order_by(DatasetColumn.column_index)
    )
    return [DatasetColumnRead.model_validate(c) for c in col_result.scalars().all()]

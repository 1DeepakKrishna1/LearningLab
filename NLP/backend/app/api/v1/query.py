"""
NLP Query endpoint.

POST /query/           — execute a natural-language query against a dataset
POST /query/sql        — execute a raw (validated) SQL query
GET  /query/history    — (stub) last N queries (can be wired to a query-log table)
"""
from __future__ import annotations

import time
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import query_cache, TTLCache
from app.core.exceptions import (
    AppError,
    DatasetNotFound,
    NLPParseError,
    QueryValidationError,
)
from app.core.security import validate_sql
from app.database import execute_dataset_query, get_db
from app.models.dataset import Dataset, DatasetColumn
from app.schemas.query import NLPQueryRequest, NLPQueryResponse, QueryResult
from app.services.nlp_engine import NLPEngine, llm_fallback_sql
from app.services.sql_generator import SQLGenerator

router = APIRouter()


def _http(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.to_dict())


async def _load_dataset_schema(
    dataset_id: str,
    db: AsyncSession,
) -> tuple[Dataset, list[DatasetColumn]]:
    """Return (dataset, columns) or raise DatasetNotFound."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise DatasetNotFound(dataset_id)

    col_result = await db.execute(
        select(DatasetColumn)
        .where(DatasetColumn.dataset_id == dataset_id)
        .order_by(DatasetColumn.column_index)
    )
    columns = list(col_result.scalars().all())
    return dataset, columns


@router.post("", response_model=NLPQueryResponse)
async def nlp_query(
    payload: NLPQueryRequest,
    db: AsyncSession = Depends(get_db),
) -> NLPQueryResponse:
    """
    Parse a natural-language query, generate SQL, execute it, and return results.
    Uses query cache keyed on (dataset_id, generated_sql).
    Falls back to LLM if rule-based NLP confidence is low and OpenAI is configured.
    """
    t0 = time.perf_counter()

    try:
        dataset, columns = await _load_dataset_schema(payload.dataset_id, db)

        if dataset.status != "ready":
            raise QueryValidationError(
                f"Dataset is not ready (status: {dataset.status}).",
                "Wait for ingestion to complete.",
                code="DATASET_NOT_READY",
            )

        col_names = [c.column_name for c in columns]
        col_types = {c.column_name: c.detected_type for c in columns}

        # ── NLP parse ────────────────────────────────────────────────────
        engine = NLPEngine(col_names, col_types)
        try:
            intent = engine.parse(payload.query)
        except NLPParseError as e:
            logger.warning("nlp_parse_failed", query=payload.query[:100], error=str(e))
            intent = None

        sql: str | None = None
        params: list[Any] = []

        if intent and intent.confidence >= 0.4:
            gen = SQLGenerator(dataset.table_name, col_names)
            try:
                sql, params = gen.build(intent, limit=payload.limit)
            except QueryValidationError as e:
                logger.warning("sql_build_failed", error=str(e))
                sql = None

        # ── LLM Fallback ─────────────────────────────────────────────────
        if not sql:
            col_schemas = [
                {
                    "name": c.column_name,
                    "type": c.detected_type,
                    "samples": c.sample_values or [],
                }
                for c in columns
            ]
            sql = await llm_fallback_sql(
                payload.query,
                dataset.table_name,
                col_schemas,
                limit=payload.limit,
            )
            if sql:
                params = []
                if intent:
                    intent.fallback_used = True
            else:
                # Last resort: full table scan
                sql = f'SELECT * FROM "{dataset.table_name}" LIMIT {min(payload.limit, 100)}'
                params = []

        # ── Validate ─────────────────────────────────────────────────────
        try:
            validated_sql = validate_sql(sql, col_names)
        except QueryValidationError as e:
            raise _http(e)

        # ── Cache lookup ─────────────────────────────────────────────────
        cache_key = query_cache.make_key(payload.dataset_id, validated_sql + str(params))
        from_cache = False

        if payload.use_cache:
            cached = await query_cache.get(cache_key)
            if cached is not None:
                elapsed = (time.perf_counter() - t0) * 1000
                cached_result = QueryResult(**cached)
                cached_result.from_cache = True
                cached_result.execution_time_ms = round(elapsed, 2)
                return NLPQueryResponse(
                    success=True,
                    query=payload.query,
                    dataset_id=payload.dataset_id,
                    result=cached_result,
                )

        # ── Execute ───────────────────────────────────────────────────────
        t_exec = time.perf_counter()
        rows = await execute_dataset_query(validated_sql, params)
        exec_ms = (time.perf_counter() - t_exec) * 1000

        result_cols = list(rows[0].keys()) if rows else []
        total_ms = (time.perf_counter() - t0) * 1000

        qr = QueryResult(
            sql=validated_sql,
            rows=rows,
            row_count=len(rows),
            columns=result_cols,
            execution_time_ms=round(total_ms, 2),
            from_cache=False,
            intent=intent,
        )

        # Store in cache
        if payload.use_cache:
            await query_cache.set(
                cache_key,
                qr.model_dump(mode="json"),
            )

        logger.info(
            "nlp_query_executed",
            dataset_id=payload.dataset_id,
            query=payload.query[:80],
            rows=len(rows),
            exec_ms=round(exec_ms, 2),
            intent=intent.intent if intent else "none",
        )

        return NLPQueryResponse(
            success=True,
            query=payload.query,
            dataset_id=payload.dataset_id,
            result=qr,
        )

    except HTTPException:
        raise
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("nlp_query_unexpected_error", query=payload.query[:80], error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={"error": "Unexpected error.", "detail": str(exc), "code": "INTERNAL_ERROR"},
        )


@router.post("/sql", response_model=NLPQueryResponse)
async def raw_sql_query(
    dataset_id: str,
    sql: str,
    limit: int = 1000,
    db: AsyncSession = Depends(get_db),
) -> NLPQueryResponse:
    """
    Execute a raw SQL SELECT (validated) against a dataset.
    Useful for widget SQL or manual queries.
    """
    t0 = time.perf_counter()
    try:
        dataset, columns = await _load_dataset_schema(dataset_id, db)
        col_names = [c.column_name for c in columns]

        validated_sql = validate_sql(sql, col_names)
        rows = await execute_dataset_query(validated_sql)
        rows = rows[:limit]

        elapsed = (time.perf_counter() - t0) * 1000
        return NLPQueryResponse(
            success=True,
            query=sql,
            dataset_id=dataset_id,
            result=QueryResult(
                sql=validated_sql,
                rows=rows,
                row_count=len(rows),
                columns=list(rows[0].keys()) if rows else [],
                execution_time_ms=round(elapsed, 2),
            ),
        )
    except HTTPException:
        raise
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("raw_sql_error", sql=sql[:200], error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={"error": "SQL execution failed.", "detail": str(exc), "code": "EXECUTION_ERROR"},
        )

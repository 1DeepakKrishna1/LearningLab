"""
Analytics API endpoints.

GET  /analytics/{dataset_id}/summary        — row count + per-column stats
GET  /analytics/{dataset_id}/correlations   — pearson correlation matrix
GET  /analytics/{dataset_id}/outliers       — IQR outlier detection for a column
GET  /analytics/{dataset_id}/timeseries     — time-series aggregation
GET  /analytics/{dataset_id}/topn           — top N groups by aggregated value
GET  /analytics/{dataset_id}/distribution   — histogram data
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.database import get_db
from app.services.analytics import AnalyticsService

router = APIRouter()


def _http(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.to_dict())


@router.get("/{dataset_id}/summary")
async def get_summary(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Overall dataset summary: row count, column stats, missing data overview."""
    try:
        svc = AnalyticsService(db)
        return await svc.get_summary_stats(dataset_id)
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("analytics_summary_error", dataset_id=dataset_id)
        raise HTTPException(status_code=500, detail={"error": str(exc), "code": "INTERNAL_ERROR"})


@router.get("/{dataset_id}/correlations")
async def get_correlations(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Pearson correlation matrix for all numeric columns."""
    try:
        svc = AnalyticsService(db)
        return await svc.get_correlations(dataset_id)
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("analytics_correlations_error", dataset_id=dataset_id)
        raise HTTPException(status_code=500, detail={"error": str(exc), "code": "INTERNAL_ERROR"})


@router.get("/{dataset_id}/outliers")
async def detect_outliers(
    dataset_id: str,
    column: str = Query(..., description="Column name to analyse for outliers"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """IQR-based outlier detection for a single numeric column."""
    try:
        svc = AnalyticsService(db)
        return await svc.detect_outliers(dataset_id, column)
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("analytics_outliers_error", dataset_id=dataset_id, column=column)
        raise HTTPException(status_code=500, detail={"error": str(exc), "code": "INTERNAL_ERROR"})


@router.get("/{dataset_id}/timeseries")
async def get_time_series(
    dataset_id: str,
    date_col: str = Query(..., description="Date/datetime column"),
    value_col: str = Query(..., description="Numeric value column to aggregate"),
    freq: str = Query(default="month", description="Grouping: day|week|month|quarter|year"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Time-series aggregation (sum, mean, count) grouped by period."""
    if freq not in {"day", "week", "month", "quarter", "year"}:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid freq.", "detail": "Use: day|week|month|quarter|year", "code": "INVALID_PARAM"},
        )
    try:
        svc = AnalyticsService(db)
        return await svc.get_time_series(dataset_id, date_col, value_col, freq)
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("analytics_timeseries_error", dataset_id=dataset_id)
        raise HTTPException(status_code=500, detail={"error": str(exc), "code": "INTERNAL_ERROR"})


@router.get("/{dataset_id}/topn")
async def get_top_n(
    dataset_id: str,
    group_col: str = Query(..., description="Column to group by"),
    value_col: str = Query(..., description="Numeric column to aggregate"),
    n: int = Query(default=10, ge=1, le=100),
    agg: str = Query(default="sum", description="sum|avg|count|max|min"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Top N groups by aggregated value."""
    if agg not in {"sum", "avg", "count", "max", "min", "mean"}:
        raise HTTPException(
            status_code=400,
            detail={"error": "Invalid agg.", "detail": "Use: sum|avg|count|max|min", "code": "INVALID_PARAM"},
        )
    try:
        svc = AnalyticsService(db)
        return await svc.get_top_n(dataset_id, group_col, value_col, n, agg)
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("analytics_topn_error", dataset_id=dataset_id)
        raise HTTPException(status_code=500, detail={"error": str(exc), "code": "INTERNAL_ERROR"})


@router.get("/{dataset_id}/distribution")
async def get_distribution(
    dataset_id: str,
    column: str = Query(..., description="Column to compute distribution for"),
    bins: int = Query(default=20, ge=2, le=200, description="Number of histogram bins"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Histogram bin data for a numeric column."""
    try:
        svc = AnalyticsService(db)
        return await svc.get_distribution(dataset_id, column, bins)
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("analytics_distribution_error", dataset_id=dataset_id, column=column)
        raise HTTPException(status_code=500, detail={"error": str(exc), "code": "INTERNAL_ERROR"})

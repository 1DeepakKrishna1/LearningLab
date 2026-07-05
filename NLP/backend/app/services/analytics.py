"""
Analytics Engine — computes derived statistics directly from the dataset
SQLite table, without loading the full dataset into memory unless needed.
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatasetNotFound, ProcessingError
from app.database import execute_dataset_query
from app.models.dataset import Dataset, DatasetColumn
from sqlalchemy import select


async def _load_dataset_df(
    db: AsyncSession,
    dataset_id: str,
    columns: list[str] | None = None,
    limit: int = 50_000,
) -> tuple[pd.DataFrame, Dataset]:
    """Load dataset rows into a DataFrame."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise DatasetNotFound(dataset_id)
    if dataset.status != "ready":
        raise ProcessingError(
            f"Dataset is not ready (status: {dataset.status}).",
            "Wait for processing to complete before running analytics.",
        )

    table = dataset.table_name
    if columns:
        col_list = ", ".join(f'"{c}"' for c in columns)
        sql = f'SELECT {col_list} FROM "{table}" LIMIT {limit}'
    else:
        sql = f'SELECT * FROM "{table}" LIMIT {limit}'

    rows = await execute_dataset_query(sql)
    df = pd.DataFrame(rows)
    return df, dataset


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary_stats(self, dataset_id: str) -> dict[str, Any]:
        """Row count, column stats overview, missing data summary."""
        df, dataset = await _load_dataset_df(self.db, dataset_id, limit=100_000)

        if df.empty:
            return {"dataset_id": dataset_id, "row_count": 0, "columns": []}

        col_stats = []
        for col in df.columns:
            series = df[col]
            total = len(series)
            null_count = int(series.isna().sum())

            stat: dict[str, Any] = {
                "column": col,
                "total": total,
                "null_count": null_count,
                "null_pct": round(null_count / total * 100, 2) if total else 0,
                "unique_count": int(series.nunique(dropna=True)),
            }

            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().sum() / max(total, 1) >= 0.5:
                stat.update(
                    {
                        "mean": _safe_float(numeric.mean()),
                        "std": _safe_float(numeric.std()),
                        "min": _safe_float(numeric.min()),
                        "max": _safe_float(numeric.max()),
                        "median": _safe_float(numeric.median()),
                        "p25": _safe_float(numeric.quantile(0.25)),
                        "p75": _safe_float(numeric.quantile(0.75)),
                    }
                )
            col_stats.append(stat)

        return {
            "dataset_id": dataset_id,
            "name": dataset.name,
            "row_count": dataset.row_count or len(df),
            "column_count": dataset.column_count or len(df.columns),
            "total_cells": (dataset.row_count or len(df)) * (dataset.column_count or len(df.columns)),
            "missing_cells": int(df.isna().sum().sum()),
            "missing_pct": round(df.isna().sum().sum() / max(df.size, 1) * 100, 2),
            "columns": col_stats,
        }

    async def get_correlations(self, dataset_id: str) -> dict[str, Any]:
        """Pearson correlation matrix for numeric columns."""
        df, _ = await _load_dataset_df(self.db, dataset_id, limit=50_000)
        if df.empty:
            return {"dataset_id": dataset_id, "matrix": {}, "columns": []}

        numeric_df = df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
        numeric_df = numeric_df.loc[:, numeric_df.nunique() > 1]

        if numeric_df.empty or numeric_df.shape[1] < 2:
            return {
                "dataset_id": dataset_id,
                "matrix": {},
                "columns": [],
                "message": "Not enough numeric columns for correlation.",
            }

        corr = numeric_df.corr(method="pearson")

        matrix: dict[str, dict[str, float | None]] = {}
        for col in corr.columns:
            matrix[col] = {}
            for row in corr.index:
                val = corr.loc[row, col]
                matrix[col][row] = _safe_float(val)

        return {
            "dataset_id": dataset_id,
            "columns": list(corr.columns),
            "matrix": matrix,
        }

    async def detect_outliers(
        self, dataset_id: str, column: str
    ) -> dict[str, Any]:
        """IQR-based outlier detection for a single numeric column."""
        df, _ = await _load_dataset_df(self.db, dataset_id, columns=[column], limit=100_000)

        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            return {
                "dataset_id": dataset_id,
                "column": column,
                "outlier_count": 0,
                "outliers": [],
            }

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outlier_mask = (series < lower) | (series > upper)
        outlier_values = series[outlier_mask].tolist()

        return {
            "dataset_id": dataset_id,
            "column": column,
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "lower_fence": round(lower, 4),
            "upper_fence": round(upper, 4),
            "outlier_count": int(outlier_mask.sum()),
            "outlier_pct": round(outlier_mask.mean() * 100, 2),
            "outlier_values": [_safe_float(v) for v in outlier_values[:200]],
        }

    async def get_time_series(
        self,
        dataset_id: str,
        date_col: str,
        value_col: str,
        freq: str = "month",
    ) -> dict[str, Any]:
        """Group by time period and aggregate a value column."""
        df, _ = await _load_dataset_df(self.db, dataset_id, columns=[date_col, value_col], limit=100_000)

        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=[date_col])

        freq_map = {
            "day": "D",
            "week": "W",
            "month": "ME",
            "quarter": "QE",
            "year": "YE",
        }
        pd_freq = freq_map.get(freq, "ME")

        grouped = (
            df.set_index(date_col)
            .resample(pd_freq)[value_col]
            .agg(["sum", "mean", "count"])
            .reset_index()
        )

        records = [
            {
                "period": str(row[date_col])[:10],
                "sum": _safe_float(row["sum"]),
                "mean": _safe_float(row["mean"]),
                "count": int(row["count"]),
            }
            for _, row in grouped.iterrows()
        ]

        return {
            "dataset_id": dataset_id,
            "date_col": date_col,
            "value_col": value_col,
            "freq": freq,
            "data": records,
        }

    async def get_top_n(
        self,
        dataset_id: str,
        group_col: str,
        value_col: str,
        n: int = 10,
        agg: str = "sum",
    ) -> dict[str, Any]:
        """Top N groups by aggregated value."""
        df, _ = await _load_dataset_df(
            self.db, dataset_id, columns=[group_col, value_col], limit=100_000
        )

        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

        agg_map = {
            "sum": "sum", "avg": "mean", "mean": "mean",
            "count": "count", "max": "max", "min": "min",
        }
        pd_agg = agg_map.get(agg.lower(), "sum")

        grouped = (
            df.groupby(group_col)[value_col]
            .agg(pd_agg)
            .reset_index()
            .sort_values(value_col, ascending=False)
            .head(n)
        )

        return {
            "dataset_id": dataset_id,
            "group_col": group_col,
            "value_col": value_col,
            "agg": agg,
            "n": n,
            "data": [
                {"group": str(row[group_col]), "value": _safe_float(row[value_col])}
                for _, row in grouped.iterrows()
            ],
        }

    async def get_distribution(
        self,
        dataset_id: str,
        column: str,
        bins: int = 20,
    ) -> dict[str, Any]:
        """Histogram data for a column."""
        df, _ = await _load_dataset_df(self.db, dataset_id, columns=[column], limit=100_000)

        series = pd.to_numeric(df[column], errors="coerce").dropna()

        if series.empty:
            return {
                "dataset_id": dataset_id,
                "column": column,
                "bins": [],
            }

        counts, bin_edges = np.histogram(series, bins=bins)

        bin_data = [
            {
                "bin_start": round(float(bin_edges[i]), 4),
                "bin_end": round(float(bin_edges[i + 1]), 4),
                "count": int(counts[i]),
            }
            for i in range(len(counts))
        ]

        return {
            "dataset_id": dataset_id,
            "column": column,
            "bins": bin_data,
            "total": int(series.count()),
            "min": _safe_float(series.min()),
            "max": _safe_float(series.max()),
            "mean": _safe_float(series.mean()),
            "std": _safe_float(series.std()),
        }


def _safe_float(val: Any) -> float | None:
    """Convert to float, return None for NaN / inf."""
    try:
        f = float(val)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 6)
    except (TypeError, ValueError):
        return None

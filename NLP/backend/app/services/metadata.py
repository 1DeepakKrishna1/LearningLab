"""
Metadata generation service.

For each column in a dataset DataFrame this service:
  - Detects the column type: numeric | categorical | datetime | text | boolean
  - Computes null%, unique count, min, max, mean, std
  - Collects up to 5 sample (non-null) values
  - Applies semantic tagging based on column name patterns
  - Persists DatasetColumn rows to the metadata database
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import DatasetColumn


# ── Type detection ────────────────────────────────────────────────────────────

def _detect_type(series: pd.Series) -> str:
    """Infer a high-level semantic type from a pandas Series."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return "text"

    # Boolean
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    unique_lower = set(str(v).strip().lower() for v in non_null.unique())
    if unique_lower.issubset({"true", "false", "yes", "no", "1", "0", "t", "f"}):
        return "boolean"

    # Numeric
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # Try coercing to numeric
    coerced = pd.to_numeric(non_null, errors="coerce")
    if coerced.notna().sum() / len(non_null) >= 0.9:
        return "numeric"

    # Datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    try:
        pd.to_datetime(non_null.head(50), infer_datetime_format=True, errors="raise")
        return "datetime"
    except Exception:
        pass

    # Categorical vs text: if unique ratio < 5% or <= 20 unique values → categorical
    unique_ratio = non_null.nunique() / len(non_null)
    if unique_ratio < 0.05 or non_null.nunique() <= 20:
        return "categorical"

    return "text"


# ── Semantic tagging ──────────────────────────────────────────────────────────

_SEMANTIC_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("id", re.compile(r"\b(id|uuid|key|identifier|pk)\b", re.IGNORECASE)),
    ("revenue", re.compile(r"\b(revenue|sales|price|amount|cost|income|profit|earning|value|fee|charge|payment)\b", re.IGNORECASE)),
    ("date", re.compile(r"\b(date|time|day|month|year|period|created|updated|timestamp|dt)\b", re.IGNORECASE)),
    ("name", re.compile(r"\b(name|title|label|description|first_name|last_name|full_name|firstname|lastname)\b", re.IGNORECASE)),
    ("email", re.compile(r"\b(email|mail|e_mail)\b", re.IGNORECASE)),
    ("phone", re.compile(r"\b(phone|mobile|cell|tel|telephone|contact)\b", re.IGNORECASE)),
    ("address", re.compile(r"\b(address|street|city|state|zip|postal|country|region|location)\b", re.IGNORECASE)),
    ("age", re.compile(r"\b(age|dob|birth|born)\b", re.IGNORECASE)),
    ("gender", re.compile(r"\b(gender|sex)\b", re.IGNORECASE)),
    ("quantity", re.compile(r"\b(quantity|qty|count|units|volume|number|num)\b", re.IGNORECASE)),
    ("category", re.compile(r"\b(category|type|class|segment|group|tier|status|kind)\b", re.IGNORECASE)),
    ("rating", re.compile(r"\b(rating|score|rank|grade|level|star)\b", re.IGNORECASE)),
]


def _semantic_tags(column_name: str) -> list[str]:
    tags = []
    for tag, pattern in _SEMANTIC_PATTERNS:
        if pattern.search(column_name):
            tags.append(tag)
    return tags


# ── Service ───────────────────────────────────────────────────────────────────

class MetadataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_column_metadata(
        self, dataset_id: str, df: pd.DataFrame
    ) -> list[DatasetColumn]:
        """
        Analyse *df* and persist one DatasetColumn row per column.
        Returns the list of created model instances.
        """
        # Remove any existing column metadata for this dataset
        from sqlalchemy import delete
        await self.db.execute(
            delete(DatasetColumn).where(DatasetColumn.dataset_id == dataset_id)
        )

        records: list[DatasetColumn] = []

        for idx, col_name in enumerate(df.columns):
            series = df[col_name]
            detected_type = _detect_type(series)

            # If stored as strings but detected numeric, coerce
            if detected_type == "numeric":
                series = pd.to_numeric(series, errors="coerce")

            total = len(series)
            null_count = series.isna().sum()
            null_pct = (null_count / total * 100) if total > 0 else 0.0
            unique_count = int(series.nunique(dropna=True))

            non_null = series.dropna()

            # Min / max
            try:
                min_val = str(non_null.min()) if len(non_null) else None
                max_val = str(non_null.max()) if len(non_null) else None
            except Exception:
                min_val = max_val = None

            # Mean / std (numeric only)
            mean_val: float | None = None
            std_val: float | None = None
            if detected_type == "numeric" and len(non_null) > 0:
                try:
                    mean_val = float(non_null.mean())
                    std_val = float(non_null.std()) if len(non_null) > 1 else 0.0
                    if np.isnan(mean_val):
                        mean_val = None
                    if std_val is not None and np.isnan(std_val):
                        std_val = None
                except Exception:
                    pass

            # Sample values (up to 5 distinct non-null)
            try:
                sample = [
                    str(v)
                    for v in non_null.unique()[:5]
                    if v is not None
                ]
            except Exception:
                sample = []

            tags = _semantic_tags(col_name)

            record = DatasetColumn(
                dataset_id=dataset_id,
                column_name=col_name,
                column_index=idx,
                detected_type=detected_type,
                null_percentage=round(null_pct, 4),
                unique_count=unique_count,
                min_value=min_val,
                max_value=max_val,
                mean_value=mean_val,
                std_value=std_val,
                sample_values=sample,
                semantic_tags=tags,
            )
            self.db.add(record)
            records.append(record)

        await self.db.flush()
        logger.info(
            "metadata_generated",
            dataset_id=dataset_id,
            columns=len(records),
        )
        return records

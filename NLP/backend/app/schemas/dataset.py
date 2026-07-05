"""
Pydantic schemas for datasets and their column metadata.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class DatasetColumnRead(BaseModel):
    id: int
    dataset_id: str
    column_name: str
    column_index: int
    detected_type: str
    null_percentage: Optional[float] = None
    unique_count: Optional[int] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    sample_values: Optional[List[Any]] = None
    semantic_tags: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class DatasetRead(BaseModel):
    id: str
    name: str
    original_filename: str
    file_size_bytes: int
    file_type: str
    status: str
    error_message: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    table_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    columns: List[DatasetColumnRead] = []

    model_config = {"from_attributes": True}


class DatasetListItem(BaseModel):
    id: str
    name: str
    original_filename: str
    file_size_bytes: int
    file_type: str
    status: str
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetStatusUpdate(BaseModel):
    status: str
    error_message: Optional[str] = None

"""
Pydantic schemas for reports and their sections.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportSectionCreate(BaseModel):
    order_index: int = Field(default=0, ge=0)
    section_type: str = Field(
        ..., description="summary|table|chart|text|stats"
    )
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[Dict[str, Any]] = None
    sql_query: Optional[str] = None


class ReportSectionRead(BaseModel):
    id: str
    report_id: str
    order_index: int
    section_type: str
    title: str
    content: Optional[Dict[str, Any]] = None
    sql_query: Optional[str] = None

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    dataset_id: str
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    sections: List[ReportSectionCreate] = []


class ReportRead(BaseModel):
    id: str
    dataset_id: str
    title: str
    description: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sections: List[ReportSectionRead] = []

    model_config = {"from_attributes": True}


class ReportUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

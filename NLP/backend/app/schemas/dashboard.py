"""
Pydantic schemas for dashboards and widgets.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GridPosition(BaseModel):
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    w: int = Field(default=6, ge=1, le=12)
    h: int = Field(default=4, ge=1)


class WidgetCreate(BaseModel):
    dataset_id: str
    title: str = Field(..., min_length=1, max_length=255)
    chart_type: str = Field(..., description="bar|line|pie|scatter|table|metric|histogram")
    sql_query: str = Field(..., min_length=1)
    config: Optional[Dict[str, Any]] = None
    grid_x: int = Field(default=0, ge=0)
    grid_y: int = Field(default=0, ge=0)
    grid_w: int = Field(default=6, ge=1, le=12)
    grid_h: int = Field(default=4, ge=1)
    nlp_prompt: Optional[str] = None


class WidgetUpdate(BaseModel):
    title: Optional[str] = None
    chart_type: Optional[str] = None
    sql_query: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    grid_x: Optional[int] = None
    grid_y: Optional[int] = None
    grid_w: Optional[int] = None
    grid_h: Optional[int] = None


class WidgetRead(BaseModel):
    id: str
    dashboard_id: str
    dataset_id: str
    title: str
    chart_type: str
    sql_query: str
    config: Optional[Dict[str, Any]] = None
    grid_x: int
    grid_y: int
    grid_w: int
    grid_h: int
    nlp_prompt: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    dataset_id: Optional[str] = None
    widgets: List[WidgetCreate] = []


class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DashboardRead(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    dataset_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    widgets: List[WidgetRead] = []

    model_config = {"from_attributes": True}


class NLPDashboardRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    dataset_id: str
    dashboard_name: Optional[str] = None

"""Segment schemas (filter builder rule tree)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

# Supported operators in the filter builder.
Operator = Literal[
    "eq", "ne", "gt", "gte", "lt", "lte",
    "contains", "not_contains", "starts_with", "ends_with",
    "in", "not_in", "is_set", "is_not_set",
]


class Condition(BaseModel):
    field: str = Field(description="contact column or attributes.<key> / tag")
    operator: Operator
    value: Any = None


class RuleGroup(BaseModel):
    op: Literal["AND", "OR"] = "AND"
    rules: list[Union["RuleGroup", Condition]] = Field(default_factory=list)


RuleGroup.model_rebuild()


class SegmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    is_dynamic: bool = True
    definition: RuleGroup = Field(default_factory=RuleGroup)


class SegmentCreate(SegmentBase):
    pass


class SegmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_dynamic: bool | None = None
    definition: RuleGroup | None = None


class SegmentOut(ORMModel):
    id: int
    name: str
    description: str
    is_dynamic: bool
    definition: dict[str, Any]
    cached_count: int | None = None
    created_at: datetime
    updated_at: datetime


class SegmentPreview(BaseModel):
    count: int
    sample: list[dict[str, Any]] = []

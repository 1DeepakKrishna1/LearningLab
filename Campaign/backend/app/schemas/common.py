"""Shared schema primitives."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = {"from_attributes": True}


class Message(BaseModel):
    message: str


class Page(BaseModel, Generic[T]):
    """Generic paginated envelope."""

    items: list[T]
    total: int
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=200)

    @property
    def pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0

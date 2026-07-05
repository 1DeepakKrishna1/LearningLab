"""Repository protocol — the storage seam.

Every persistent entity is a Pydantic model exposing a string `id`. Services depend
on `Repository[T]`, never on a concrete backend, so storage can be swapped freely.
"""
from __future__ import annotations

from typing import Callable, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel


class Identifiable(Protocol):
    id: str


T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class Repository(Protocol, Generic[T]):
    """Async CRUD contract for a collection of entities of type `T`."""

    async def get(self, entity_id: str) -> T | None: ...

    async def list(self) -> list[T]: ...

    async def find(self, predicate: Callable[[T], bool]) -> list[T]: ...

    async def add(self, entity: T) -> T: ...

    async def update(self, entity: T) -> T: ...

    async def delete(self, entity_id: str) -> bool: ...

    async def count(self) -> int: ...

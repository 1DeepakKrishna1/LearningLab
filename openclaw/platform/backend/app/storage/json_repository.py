"""JSON-file backed repository implementation.

Each repository owns exactly one JSON file holding an object keyed by entity id:

    { "<id>": { ...entity... }, ... }

Concurrency: an in-process ``asyncio.Lock`` serialises mutations, and writes are
atomic (write to a temp file, then ``os.replace``) so a crash mid-write cannot
corrupt the store. This is appropriate for the single-process JSON backend; the
``Repository`` seam lets a multi-process DB backend replace it later.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Callable, Generic, Type, TypeVar

from pydantic import BaseModel

from ..logging_setup import get_logger
from .repository import Repository

T = TypeVar("T", bound=BaseModel)
logger = get_logger("storage.json")


class JsonRepository(Repository[T], Generic[T]):
    """A `Repository[T]` persisted to a single JSON file."""

    def __init__(self, file_path: Path, model: Type[T]) -> None:
        self._path = file_path
        self._model = model
        self._lock = asyncio.Lock()
        self._cache: dict[str, T] | None = None
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # --- internal load/save (caller holds the lock for mutations) ---
    def _load_unlocked(self) -> dict[str, T]:
        if self._cache is not None:
            return self._cache
        if not self._path.exists():
            self._cache = {}
            return self._cache
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8") or "{}")
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read %s (%s); starting empty.", self._path.name, exc)
            raw = {}
        self._cache = {
            key: self._model.model_validate(value) for key, value in raw.items()
        }
        return self._cache

    def _save_unlocked(self) -> None:
        assert self._cache is not None
        serialisable = {k: v.model_dump(mode="json") for k, v in self._cache.items()}
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(serialisable, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._path)  # atomic on the same filesystem

    @staticmethod
    def _id_of(entity: T) -> str:
        return getattr(entity, "id")

    # --- Repository API ---
    async def get(self, entity_id: str) -> T | None:
        async with self._lock:
            return self._load_unlocked().get(entity_id)

    async def list(self) -> list[T]:
        async with self._lock:
            return list(self._load_unlocked().values())

    async def find(self, predicate: Callable[[T], bool]) -> list[T]:
        async with self._lock:
            return [e for e in self._load_unlocked().values() if predicate(e)]

    async def add(self, entity: T) -> T:
        async with self._lock:
            data = self._load_unlocked()
            eid = self._id_of(entity)
            if eid in data:
                raise KeyError(f"{self._model.__name__} '{eid}' already exists")
            data[eid] = entity
            self._save_unlocked()
            return entity

    async def update(self, entity: T) -> T:
        async with self._lock:
            data = self._load_unlocked()
            eid = self._id_of(entity)
            if eid not in data:
                raise KeyError(f"{self._model.__name__} '{eid}' not found")
            data[eid] = entity
            self._save_unlocked()
            return entity

    async def upsert(self, entity: T) -> T:
        async with self._lock:
            data = self._load_unlocked()
            data[self._id_of(entity)] = entity
            self._save_unlocked()
            return entity

    async def delete(self, entity_id: str) -> bool:
        async with self._lock:
            data = self._load_unlocked()
            if entity_id in data:
                del data[entity_id]
                self._save_unlocked()
                return True
            return False

    async def count(self) -> int:
        async with self._lock:
            return len(self._load_unlocked())

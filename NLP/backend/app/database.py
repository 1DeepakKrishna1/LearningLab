"""
Database setup: async SQLAlchemy engine + session factory, plus a raw
aiosqlite helper for running queries against per-dataset tables.
"""
from __future__ import annotations

import aiosqlite
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# ── SQLAlchemy async engine (metadata DB) ─────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:  # type: ignore[return]
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Dataset-table helpers (raw aiosqlite) ────────────────────────────────────

def _db_path() -> str:
    """Extract the file path from the DATABASE_URL for aiosqlite."""
    url = settings.database_url
    # sqlite+aiosqlite:///./foo.db  →  ./foo.db
    return url.split("///", 1)[-1]


async def get_dataset_connection() -> aiosqlite.Connection:  # type: ignore[return]
    """
    Open a raw aiosqlite connection to the metadata database.
    Callers are responsible for closing it.
    """
    conn = await aiosqlite.connect(_db_path())
    conn.row_factory = aiosqlite.Row
    return conn


async def execute_dataset_query(
    sql: str,
    parameters: tuple | list | None = None,
) -> list[dict]:
    """
    Execute a read-only query against the dataset tables and return rows
    as a list of plain dicts.  Uses a short-lived connection.
    """
    async with aiosqlite.connect(_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(sql, parameters or ()) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def init_db() -> None:
    """Create all metadata tables on startup."""
    from app.models import dataset, dashboard, report  # noqa: F401 — triggers table registration

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

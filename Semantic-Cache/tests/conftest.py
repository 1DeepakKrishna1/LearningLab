"""
Shared pytest fixtures.

Requirements:
    pip install pytest pytest-asyncio

Set REDIS_URL env var if not using localhost:6379/0.
Each test run uses a unique key prefix to avoid inter-test pollution.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from semantic_cache.config import Settings
from semantic_cache.store.redis_store import RedisStore


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as requiring a live Redis instance"
    )


@pytest.fixture
def unique_prefix() -> str:
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_settings(unique_prefix: str) -> Settings:
    return Settings(
        REDIS_URL="redis://localhost:6379/0",
        KEY_PREFIX=unique_prefix,
        HIGH_TH=0.9,
        LOW_TH=0.7,
        TOP_K=5,
        DEFAULT_TTL=60,
        EMBEDDING_PROVIDER="openai",
        VECTOR_DIM=4,  # tiny dim for tests
    )


@pytest_asyncio.fixture
async def redis_store(test_settings: Settings):
    store = RedisStore(
        redis_url=test_settings.redis_url,
        key_prefix=test_settings.key_prefix,
    )
    await store.connect()
    yield store
    await store.flush()
    await store.close()

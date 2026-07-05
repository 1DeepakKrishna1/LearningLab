"""Shared pytest fixtures."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from app.config import Settings
from app.container import Container


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", jwt_secret="test-secret")


@pytest_asyncio.fixture
async def container(settings: Settings) -> Container:
    c = Container(settings)
    await c.startup()
    return c


@pytest.fixture
def client(settings: Settings, monkeypatch):
    """A FastAPI TestClient whose container uses a temp data dir."""
    from fastapi.testclient import TestClient
    from app import main as main_module

    # main.py binds get_settings at import time; patch its reference + the source.
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    app = main_module.create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client, settings: Settings) -> dict:
    resp = client.post("/api/auth/login", json={
        "email": settings.bootstrap_admin_email,
        "password": settings.bootstrap_admin_password,
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

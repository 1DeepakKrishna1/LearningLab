"""Pytest fixtures: isolated SQLite DB + authenticated test client."""
from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force a temp database + disable the scheduler before importing the app.
_tmp_db = os.path.join(tempfile.gettempdir(), "campaign_test.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["ENABLE_SCHEDULER"] = "false"

from app.core import database  # noqa: E402
from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
_settings = get_settings()

# Rebind the engine/session to the test DB.
database.engine = create_engine(_settings.DATABASE_URL, connect_args={"check_same_thread": False})
database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import run as seed_run  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_run()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _token(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def admin_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'admin@local', 'Admin@123')}"}


@pytest.fixture
def marketer_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'marketer@local', 'Marketer@123')}"}


@pytest.fixture
def viewer_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'viewer@local', 'Viewer@123')}"}

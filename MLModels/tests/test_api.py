"""Smoke tests for the FastAPI interface (predict + retrain)."""

from __future__ import annotations

import importlib

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from app_detector import api as api_module  # noqa: E402
from app_detector.datagen import generate_master, generate_training  # noqa: E402
from app_detector.model import save_model, train_model  # noqa: E402

FEATURES_INPUT = {
    "employment_status": "employed",
    "income_bracket": "high",
    "credit_history": "good",
    "loan_purpose": "home",
    "residence_type": "own",
    "region": "north",
    "existing_customer": "yes",
    "device_type": "mobile",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient backed by a freshly trained model in a temp file."""
    master = generate_master(count=200, seed=42)
    training = generate_training(master, count=80, seed=7)
    model_path = tmp_path / "model.json"
    save_model(train_model(training), model_path)

    monkeypatch.setattr(api_module, "MODEL_PATH", str(model_path))
    monkeypatch.setattr(api_module, "store", api_module._ModelStore(str(model_path)))
    return TestClient(api_module.app), training


def test_health(client):
    c, _ = client
    assert c.get("/health").json()["status"] == "ok"


def test_predict_returns_decision(client):
    c, training = client
    resp = c.post("/predict", json={k: training[0][k] for k in FEATURES_INPUT})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {
        "application_id", "ai_decision", "recommended_action", "confidence", "signals",
    }
    assert 0.0 <= body["confidence"] <= 1.0


def test_predict_missing_feature_is_422(client):
    c, _ = client
    assert c.post("/predict", json={"employment_status": "employed"}).status_code == 422


def test_retrain_single_record_with_weight_raises_confidence(client):
    c, _ = client
    record = {**FEATURES_INPUT, "application_id": "APP-HITL-1"}

    r = c.post("/retrain", json={"records": record, "weight": 6})
    assert r.status_code == 200
    body = r.json()
    assert body["records_applied"] == 1
    assert body["new_classes"] == 1

    pred = c.post("/predict", json=FEATURES_INPUT).json()
    assert pred["application_id"] == "APP-HITL-1"
    assert pred["confidence"] >= 0.75  # upweighted HITL correction -> Low Risk


def test_retrain_accepts_list(client):
    c, _ = client
    records = [
        {**FEATURES_INPUT, "application_id": "APP-HITL-A"},
        {**FEATURES_INPUT, "income_bracket": "low", "application_id": "APP-HITL-B"},
    ]
    r = c.post("/retrain", json={"records": records})
    assert r.status_code == 200
    assert r.json()["records_applied"] == 2

"""FastAPI interface for app-detector: ``/predict`` and ``/retrain``.

Wraps the same model/decision logic the CLI uses behind an HTTP API, so the
service can be embedded in another system or called from a notebook/UI.

Run it::

    app-detector-api                      # serves on 0.0.0.0:9000
    # or:
    uvicorn app_detector.api:app --port 9000

The model file the server reads/writes defaults to ``model.json`` and can be
overridden with the ``APP_DETECTOR_MODEL`` environment variable. Interactive
docs are available at http://localhost:9000/docs once running.
"""

from __future__ import annotations

import os
import threading
from typing import Dict, List, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .config import FEATURE_NAMES, FEATURES
from .decision import build_decision
from .model import LABEL_KEY, load_model, retrain_model, save_model

MODEL_PATH = os.environ.get("APP_DETECTOR_MODEL", "model.json")

app = FastAPI(
    title="app-detector",
    version="1.0.0",
    description="Naive Bayes application_id detection with risk/action decisioning.",
)


# ---------------------------------------------------------------------------
# Thread-safe model cache (load once; refresh after a retrain)
# ---------------------------------------------------------------------------
class _ModelStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._model = None  # lazily loaded

    def get(self):
        with self._lock:
            if self._model is None:
                self._model = self._load()
            return self._model

    def _load(self):
        try:
            return load_model(self.path)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"model not found at '{self.path}'. Train one first "
                       f"(app-detector train) or set APP_DETECTOR_MODEL.",
            ) from exc

    def retrain(self, records: List[Dict[str, str]], weight: int):
        with self._lock:
            model = self._model or self._load()
            retrain_model(model, records, weight=weight)
            save_model(model, self.path)
            self._model = model
            return model


store = _ModelStore(MODEL_PATH)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
# The 8 categorical features, declared explicitly so they show up in the docs.
class Features(BaseModel):
    employment_status: str
    income_bracket: str
    credit_history: str
    loan_purpose: str
    residence_type: str
    region: str
    existing_customer: str
    device_type: str

    def to_features(self) -> Dict[str, str]:
        data = self.model_dump()
        return {f: str(data[f]) for f in FEATURE_NAMES}


class LabelledRecord(Features):
    application_id: str = Field(..., description="True application_id for this record.")

    def to_record(self) -> Dict[str, str]:
        rec = self.to_features()
        rec[LABEL_KEY] = self.application_id
        return rec


class Decision(BaseModel):
    application_id: str
    ai_decision: str
    recommended_action: str
    confidence: float
    signals: List[str]


class RetrainRequest(BaseModel):
    # Accept either a single record or a list of records.
    records: Union[LabelledRecord, List[LabelledRecord]]
    weight: int = Field(1, ge=1, description="Count each record this many times (upweight trusted corrections).")


class RetrainResponse(BaseModel):
    # "model_path" would otherwise collide with pydantic's protected "model_" namespace.
    model_config = ConfigDict(protected_namespaces=())

    records_applied: int
    weight: int
    n_samples: int
    classes: int
    new_classes: int
    model_path: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "model_path": MODEL_PATH}


@app.get("/features")
def features() -> Dict[str, List[str]]:
    """The feature schema (allowed values per feature)."""
    return {name: list(values) for name, values in FEATURES.items()}


@app.post("/predict", response_model=Decision)
def predict(body: Features) -> Decision:
    """Detect an application_id + risk/action decision for a feature input."""
    model = store.get()
    decision = build_decision(model, body.to_features())
    return Decision(**decision)


@app.post("/retrain", response_model=RetrainResponse)
def retrain(body: RetrainRequest) -> RetrainResponse:
    """Fold additional (e.g. HITL) labelled records into the trained model.

    The update is incremental and persisted to the server's model file.
    """
    items = body.records if isinstance(body.records, list) else [body.records]
    if not items:
        raise HTTPException(status_code=400, detail="no records provided")
    records = [r.to_record() for r in items]

    classes_before = len(store.get().classes_)
    model = store.retrain(records, weight=body.weight)
    return RetrainResponse(
        records_applied=len(records),
        weight=body.weight,
        n_samples=model.n_samples_,
        classes=len(model.classes_),
        new_classes=len(model.classes_) - classes_before,
        model_path=MODEL_PATH,
    )


def serve() -> None:
    """Console-script entry point: run the API on 0.0.0.0:9000."""
    import uvicorn

    host = os.environ.get("APP_DETECTOR_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_DETECTOR_PORT", "9000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    serve()

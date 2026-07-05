"""Training / persistence / evaluation orchestration around the NB classifier."""

from __future__ import annotations

from typing import Dict, List, Mapping, Sequence

from . import __version__
from .config import FEATURE_NAMES, feature_vocab_sizes
from .io_utils import PathLike, read_json, write_json
from .nb import CategoricalNaiveBayes

LABEL_KEY = "application_id"


def train_model(training_records: Sequence[Mapping[str, str]], *, alpha: float = 1.0) -> CategoricalNaiveBayes:
    """Fit a Categorical Naive Bayes model on labelled training records."""
    model = CategoricalNaiveBayes(
        feature_names=list(FEATURE_NAMES),
        vocab_sizes=feature_vocab_sizes(),
        alpha=alpha,
    )
    model.fit(training_records, label_key=LABEL_KEY)
    return model


def retrain_model(
    model: CategoricalNaiveBayes,
    records: Sequence[Mapping[str, str]],
    *,
    weight: int = 1,
) -> CategoricalNaiveBayes:
    """Fold additional labelled ``records`` into an already-trained model.

    Returns the same model instance, updated in place. Equivalent to training
    from scratch on the original corpus plus ``records`` — handy for applying
    human-in-the-loop (HITL) corrections on top of an existing model. ``weight``
    counts each record multiple times to give trusted corrections more pull.
    """
    model.partial_fit(records, label_key=LABEL_KEY, weight=weight)
    return model


def save_model(model: CategoricalNaiveBayes, path: PathLike) -> None:
    """Persist the model to ``path`` as JSON (with a small metadata envelope)."""
    payload = {
        "schema_version": __version__,
        "model": model.to_dict(),
    }
    write_json(path, payload)


def load_model(path: PathLike) -> CategoricalNaiveBayes:
    """Load a model previously saved with :func:`save_model`."""
    payload = read_json(path)
    if "model" not in payload:
        raise ValueError(f"{path} does not look like an app-detector model file")
    return CategoricalNaiveBayes.from_dict(payload["model"])


def evaluate(model: CategoricalNaiveBayes, records: Sequence[Mapping[str, str]]) -> Dict:
    """Top-1 accuracy of ``model`` over labelled ``records``."""
    if not records:
        raise ValueError("cannot evaluate on an empty set")
    correct = 0
    misses: List[Dict[str, str]] = []
    for row in records:
        predicted, _ = model.predict(row)
        actual = row.get(LABEL_KEY)
        if predicted == actual:
            correct += 1
        else:
            misses.append({"expected": actual, "predicted": predicted})
    total = len(records)
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 4),
        "sample_misses": misses[:10],
    }


def extract_features(record: Mapping[str, str]) -> Dict[str, str]:
    """Pull just the model features out of a record, validating completeness."""
    missing = [f for f in FEATURE_NAMES if f not in record]
    if missing:
        raise ValueError(f"input is missing required feature(s): {', '.join(missing)}")
    return {f: str(record[f]) for f in FEATURE_NAMES}

import math

import pytest

from app_detector.nb import CategoricalNaiveBayes


def _model():
    return CategoricalNaiveBayes(
        feature_names=["color", "shape"],
        vocab_sizes={"color": 3, "shape": 2},
        alpha=1.0,
    )


TRAIN = [
    {"color": "red", "shape": "round", "application_id": "A"},
    {"color": "red", "shape": "round", "application_id": "A"},
    {"color": "blue", "shape": "square", "application_id": "B"},
    {"color": "blue", "shape": "square", "application_id": "B"},
]


def test_fit_counts():
    m = _model().fit(TRAIN)
    assert m.classes_ == ["A", "B"]
    assert m.class_counts_ == {"A": 2, "B": 2}
    assert m.n_samples_ == 4
    assert m.seen_value("color", "A", "red")
    assert not m.seen_value("color", "A", "blue")


def test_predict_picks_matching_class():
    m = _model().fit(TRAIN)
    label, prob = m.predict({"color": "red", "shape": "round"})
    assert label == "A"
    assert prob > 0.5


def test_predict_proba_sums_to_one():
    m = _model().fit(TRAIN)
    proba = m.predict_proba({"color": "blue", "shape": "square"})
    assert math.isclose(sum(proba.values()), 1.0, rel_tol=1e-9)
    assert max(proba, key=proba.get) == "B"


def test_ranked_is_sorted_descending():
    m = _model().fit(TRAIN)
    ranked = m.predict_ranked({"color": "red", "shape": "round"})
    probs = [p for _, p in ranked]
    assert probs == sorted(probs, reverse=True)


def test_round_trip_serialisation():
    m = _model().fit(TRAIN)
    restored = CategoricalNaiveBayes.from_dict(m.to_dict())
    assert restored.predict_proba({"color": "red", "shape": "round"}) == \
        m.predict_proba({"color": "red", "shape": "round"})


def test_missing_feature_raises():
    m = _model().fit(TRAIN)
    with pytest.raises(ValueError):
        m.predict({"color": "red"})


def test_fit_empty_raises():
    with pytest.raises(ValueError):
        _model().fit([])


def test_unfitted_predict_raises():
    with pytest.raises(RuntimeError):
        _model().predict_proba({"color": "red", "shape": "round"})

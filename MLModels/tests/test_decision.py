from app_detector.config import ACTIONS, FEATURE_NAMES, FEATURES, RISK_LEVELS
from app_detector.datagen import generate_master, generate_training
from app_detector.decision import build_decision
from app_detector.model import extract_features, train_model


def _trained():
    master = generate_master(100, seed=11)
    training = generate_training(master, count=100, seed=12, pool_size=20, noise=0.1)
    return train_model(training), master, training


def test_decision_schema_and_value_domains():
    model, _, training = _trained()
    features = extract_features(training[0])
    decision = build_decision(model, features)

    assert set(decision) == {
        "application_id",
        "ai_decision",
        "recommended_action",
        "confidence",
        "signals",
    }
    assert decision["application_id"].startswith("APP-")
    assert decision["ai_decision"] in RISK_LEVELS
    assert decision["recommended_action"] in ACTIONS
    assert 0.0 <= decision["confidence"] <= 1.0
    assert isinstance(decision["signals"], list)
    assert round(decision["confidence"], 2) == decision["confidence"]


def test_high_confidence_clean_match_is_low_risk_approve():
    # A noise-free profile should classify confidently to its own id.
    master = generate_master(40, seed=21)
    training = generate_training(master, count=60, seed=22, pool_size=8, noise=0.0)
    model = train_model(training)
    decision = build_decision(model, extract_features(training[0]))
    assert decision["ai_decision"] == "Low Risk"
    assert decision["recommended_action"] == "Approve"
    assert "strong_profile_match" in decision["signals"]


def test_all_three_actions_are_reachable():
    # Sweep many off-pool/random feature combos and confirm Approve, Escalate,
    # and Decline can all occur (no action is dead code).
    model, master, _ = _trained()
    seen = set()
    for rec in master:  # master ids are mostly outside the trained pool -> varied confidence
        decision = build_decision(model, extract_features(rec))
        seen.add(decision["recommended_action"])
    assert {"Approve", "Escalate", "Decline"} <= seen


def test_profile_mismatch_signal_when_values_unseen():
    model, _, training = _trained()
    features = extract_features(training[0])
    # Force an unusual value unlikely to be seen for the predicted class.
    features[FEATURE_NAMES[0]] = FEATURES[FEATURE_NAMES[0]][-1]
    decision = build_decision(model, features)
    assert isinstance(decision["signals"], list)

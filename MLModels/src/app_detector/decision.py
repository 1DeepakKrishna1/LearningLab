"""Turn a classifier prediction into the business decision payload.

Maps the Naive Bayes output (top application_id, posterior distribution, and
feature match quality) onto the required schema:

    {
      "application_id": "APP-80637",
      "ai_decision": "Low Risk",
      "recommended_action": "Escalate",
      "confidence": 0.76,
      "signals": ["edge_case_flag", "manual_review_recommended"]
    }
"""

from __future__ import annotations

from typing import Dict, List, Mapping

from .config import (
    EDGE_CASE_MARGIN,
    FEATURE_NAMES,
    LOW_CONFIDENCE_THRESHOLD,
    RISK_LOW_THRESHOLD,
    RISK_MED_THRESHOLD,
)
from .nb import CategoricalNaiveBayes


def _risk_from_confidence(confidence: float) -> str:
    if confidence >= RISK_LOW_THRESHOLD:
        return "Low Risk"
    if confidence >= RISK_MED_THRESHOLD:
        return "Medium Risk"
    return "High Risk"


def _collect_signals(
    model: CategoricalNaiveBayes,
    features: Mapping[str, str],
    label: str,
    confidence: float,
    margin: float,
) -> List[str]:
    """Derive explainability signals from match quality and confidence."""
    signals: List[str] = []

    # Two top candidates are nearly tied -> ambiguous classification.
    if margin < EDGE_CASE_MARGIN:
        signals.append("edge_case_flag")

    # Borderline-but-salvageable confidence: a human can likely resolve it.
    # (Below this band the match is too weak to be worth manual review.)
    if LOW_CONFIDENCE_THRESHOLD <= confidence < RISK_MED_THRESHOLD:
        signals.append("manual_review_recommended")

    # Too weak to act on automatically and not worth manual review.
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        signals.append("low_confidence_match")

    # Any observed feature value never seen for this class during training.
    mismatches = [f for f in FEATURE_NAMES if not model.seen_value(f, label, features[f])]
    if mismatches:
        signals.append("profile_mismatch")

    # The matched application was supported by very little training data.
    if model.class_support(label) <= 1:
        signals.append("sparse_training_signal")

    # A clean, confident, fully-matching prediction.
    if not signals and confidence >= RISK_LOW_THRESHOLD:
        signals.append("strong_profile_match")

    return signals


def _recommend_action(risk: str, signals: List[str]) -> str:
    # Ambiguity or a flagged-for-review case always goes to a human.
    if "edge_case_flag" in signals or "manual_review_recommended" in signals:
        return "Escalate"
    if risk == "High Risk":
        # High risk with no salvageable signal (confidence too weak to review):
        # the system cannot confidently identify the application -> auto-decline.
        return "Decline"
    if risk == "Low Risk":
        return "Approve"
    return "Escalate"  # Medium Risk with no blocking signals


def build_decision(model: CategoricalNaiveBayes, features: Mapping[str, str]) -> Dict:
    """Produce the full decision payload for a single feature observation."""
    ranked = model.predict_ranked(features)
    top_label, top_prob = ranked[0]
    runner_up_prob = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = top_prob - runner_up_prob

    confidence = round(top_prob, 2)
    risk = _risk_from_confidence(top_prob)
    signals = _collect_signals(model, features, top_label, top_prob, margin)
    action = _recommend_action(risk, signals)

    return {
        "application_id": top_label,
        "ai_decision": risk,
        "recommended_action": action,
        "confidence": confidence,
        "signals": signals,
    }

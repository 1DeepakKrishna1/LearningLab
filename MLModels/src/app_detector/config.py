"""Static configuration: the feature schema and decision thresholds.

Centralising these makes the rest of the package data-driven: add or change a
feature in one place and generation, training, and prediction all follow.
"""

from __future__ import annotations

from typing import Dict, List, Mapping

# ---------------------------------------------------------------------------
# Feature schema
# ---------------------------------------------------------------------------
# Eight categorical (string) features modelling a credit/loan application.
# Order is preserved and used consistently throughout the package.
FEATURES: Mapping[str, List[str]] = {
    "employment_status": ["employed", "self_employed", "unemployed", "retired", "student"],
    "income_bracket": ["low", "medium", "high", "very_high"],
    "credit_history": ["excellent", "good", "fair", "poor", "none"],
    "loan_purpose": ["home", "auto", "education", "business", "personal", "debt_consolidation"],
    "residence_type": ["own", "mortgage", "rent", "family"],
    "region": ["north", "south", "east", "west", "central"],
    "existing_customer": ["yes", "no"],
    "device_type": ["mobile", "desktop", "tablet"],
}

FEATURE_NAMES: List[str] = list(FEATURES.keys())

APPLICATION_ID_PREFIX = "APP-"

# ---------------------------------------------------------------------------
# Decision thresholds
# ---------------------------------------------------------------------------
# Risk tiers derived from the classifier's top posterior probability (confidence).
RISK_LOW_THRESHOLD = 0.75   # confidence >= this  -> "Low Risk"
RISK_MED_THRESHOLD = 0.50   # confidence >= this  -> "Medium Risk", else "High Risk"

# Signal thresholds.
EDGE_CASE_MARGIN = 0.10     # top1 - top2 probability below this -> ambiguous match
LOW_CONFIDENCE_THRESHOLD = 0.35

RISK_LEVELS = ("High Risk", "Medium Risk", "Low Risk")
ACTIONS = ("Decline", "Approve", "Escalate")


def feature_vocab_sizes() -> Dict[str, int]:
    """Number of distinct values per feature (used for Laplace smoothing)."""
    return {name: len(values) for name, values in FEATURES.items()}

"""Categorical Naive Bayes classifier (pure Python, Laplace-smoothed).

Implements the standard categorical NB:

    score(c | x) = log P(c) + sum_f log P(x_f | c)

with add-alpha (Laplace) smoothing per feature:

    P(c)       = (n_c + alpha) / (N + alpha * K)
    P(v | c)   = (n_{c,f,v} + alpha) / (n_c + alpha * V_f)

where K is the number of classes and V_f the vocabulary size of feature f.
Scores are converted to a posterior distribution with a numerically stable
softmax so the top probability is a usable confidence value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence, Tuple


@dataclass
class CategoricalNaiveBayes:
    """A Laplace-smoothed categorical Naive Bayes classifier.

    Attributes are plain dicts/lists so the model serialises cleanly to JSON.
    """

    feature_names: List[str]
    # Known vocabulary size per feature (drives smoothing; covers unseen values).
    vocab_sizes: Dict[str, int]
    alpha: float = 1.0

    classes_: List[str] = field(default_factory=list)
    class_counts_: Dict[str, int] = field(default_factory=dict)
    # feature -> class -> value -> count
    value_counts_: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=dict)
    n_samples_: int = 0

    # -- training ----------------------------------------------------------
    def fit(self, records: Sequence[Mapping[str, str]], label_key: str = "application_id") -> "CategoricalNaiveBayes":
        """Fit the model from labelled ``records``.

        Each record maps every feature name to a string value and includes
        ``label_key`` holding the target class.
        """
        if not records:
            raise ValueError("cannot fit on an empty training set")

        self.class_counts_ = {}
        self.value_counts_ = {f: {} for f in self.feature_names}
        self.n_samples_ = 0

        for row in records:
            label = row.get(label_key)
            if label is None:
                raise ValueError(f"record missing label '{label_key}': {row}")
            self.class_counts_[label] = self.class_counts_.get(label, 0) + 1
            self.n_samples_ += 1
            for feature in self.feature_names:
                value = row.get(feature)
                if value is None:
                    raise ValueError(f"record missing feature '{feature}': {row}")
                per_class = self.value_counts_[feature].setdefault(label, {})
                per_class[value] = per_class.get(value, 0) + 1

        self.classes_ = sorted(self.class_counts_)
        return self

    def partial_fit(
        self,
        records: Sequence[Mapping[str, str]],
        label_key: str = "application_id",
        weight: int = 1,
    ) -> "CategoricalNaiveBayes":
        """Update an already-fitted model with additional labelled ``records``.

        Because categorical NB stores only counts, incremental training is
        exact: new observations simply add to the existing class/value tallies
        (no information is lost and the result is identical to training on the
        concatenated corpus). New classes unseen during the original fit are
        added automatically. Use this to fold in human-in-the-loop corrections.

        ``weight`` controls how many times each record is counted (default 1).
        A higher weight makes a human-verified correction dominate the prior
        evidence faster, raising the model's confidence in that label.
        """
        if not records:
            raise ValueError("cannot update on an empty record set")
        if weight < 1:
            raise ValueError(f"weight must be a positive integer, got {weight}")
        # Ensure containers exist even if called on a freshly constructed model.
        for feature in self.feature_names:
            self.value_counts_.setdefault(feature, {})

        for row in records:
            label = row.get(label_key)
            if label is None:
                raise ValueError(f"record missing label '{label_key}': {row}")
            self.class_counts_[label] = self.class_counts_.get(label, 0) + weight
            self.n_samples_ += weight
            for feature in self.feature_names:
                value = row.get(feature)
                if value is None:
                    raise ValueError(f"record missing feature '{feature}': {row}")
                per_class = self.value_counts_[feature].setdefault(label, {})
                per_class[value] = per_class.get(value, 0) + weight

        self.classes_ = sorted(self.class_counts_)
        return self

    # -- inference ---------------------------------------------------------
    def _log_prior(self, label: str) -> float:
        k = len(self.classes_)
        return math.log(
            (self.class_counts_[label] + self.alpha) / (self.n_samples_ + self.alpha * k)
        )

    def _log_likelihood(self, feature: str, value: str, label: str) -> float:
        n_c = self.class_counts_[label]
        v_f = self.vocab_sizes[feature]
        count = self.value_counts_[feature].get(label, {}).get(value, 0)
        return math.log((count + self.alpha) / (n_c + self.alpha * v_f))

    def joint_log_scores(self, features: Mapping[str, str]) -> Dict[str, float]:
        """Unnormalised log joint score per class for the given features."""
        if not self.classes_:
            raise RuntimeError("model is not fitted")
        scores: Dict[str, float] = {}
        for label in self.classes_:
            total = self._log_prior(label)
            for feature in self.feature_names:
                value = features.get(feature)
                if value is None:
                    raise ValueError(f"missing feature '{feature}' in input")
                total += self._log_likelihood(feature, value, label)
            scores[label] = total
        return scores

    def predict_proba(self, features: Mapping[str, str]) -> Dict[str, float]:
        """Posterior probability per class via a numerically stable softmax."""
        scores = self.joint_log_scores(features)
        max_score = max(scores.values())
        exps = {label: math.exp(s - max_score) for label, s in scores.items()}
        total = sum(exps.values())
        return {label: val / total for label, val in exps.items()}

    def predict_ranked(self, features: Mapping[str, str]) -> List[Tuple[str, float]]:
        """All classes ranked by posterior probability (descending)."""
        proba = self.predict_proba(features)
        return sorted(proba.items(), key=lambda kv: kv[1], reverse=True)

    def predict(self, features: Mapping[str, str]) -> Tuple[str, float]:
        """Return the single most probable ``(application_id, probability)``."""
        return self.predict_ranked(features)[0]

    # -- introspection helpers --------------------------------------------
    def seen_value(self, feature: str, label: str, value: str) -> bool:
        """Whether ``value`` was observed for ``label`` during training."""
        return self.value_counts_.get(feature, {}).get(label, {}).get(value, 0) > 0

    def class_support(self, label: str) -> int:
        """Number of training samples observed for ``label``."""
        return self.class_counts_.get(label, 0)

    # -- persistence -------------------------------------------------------
    def to_dict(self) -> Dict:
        return {
            "type": "CategoricalNaiveBayes",
            "alpha": self.alpha,
            "feature_names": self.feature_names,
            "vocab_sizes": self.vocab_sizes,
            "classes": self.classes_,
            "class_counts": self.class_counts_,
            "value_counts": self.value_counts_,
            "n_samples": self.n_samples_,
        }

    @classmethod
    def from_dict(cls, data: Mapping) -> "CategoricalNaiveBayes":
        model = cls(
            feature_names=list(data["feature_names"]),
            vocab_sizes=dict(data["vocab_sizes"]),
            alpha=float(data.get("alpha", 1.0)),
        )
        model.classes_ = list(data["classes"])
        model.class_counts_ = dict(data["class_counts"])
        model.value_counts_ = {
            f: {c: dict(vals) for c, vals in per_class.items()}
            for f, per_class in data["value_counts"].items()
        }
        model.n_samples_ = int(data["n_samples"])
        return model

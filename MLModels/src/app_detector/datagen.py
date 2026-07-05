"""Synthetic data generation.

Two artifacts are produced:

  * **Master catalog** - ~N applications, each a unique ``application_id`` paired
    with a canonical profile of one value per feature.
  * **Training set**   - ~M labelled observations. Each row samples an application
    from a learnable pool and emits its profile with a little per-feature noise,
    so the Naive Bayes model has repeated, slightly noisy signal to learn from.

All randomness is seeded for fully reproducible output.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from .config import APPLICATION_ID_PREFIX, FEATURE_NAMES, FEATURES

# A fixed-width numeric id keeps ids stable and human-readable (e.g. APP-80637).
_ID_WIDTH = 5
_MAX_IDS = 10 ** _ID_WIDTH  # 100000 distinct ids available


def _make_application_id(number: int) -> str:
    return f"{APPLICATION_ID_PREFIX}{number:0{_ID_WIDTH}d}"


def generate_master(count: int = 1000, *, seed: int = 42) -> List[Dict[str, str]]:
    """Generate ``count`` master application records with unique ids and profiles.

    Each record is ``{"application_id": "APP-#####", <feature>: <value>, ...}``.
    """
    if count <= 0:
        raise ValueError("count must be a positive integer")
    if count > _MAX_IDS:
        raise ValueError(f"count must not exceed {_MAX_IDS} (id space limit)")

    rng = random.Random(seed)
    # Unique, shuffled ids so they look realistic rather than strictly sequential.
    id_numbers = rng.sample(range(_MAX_IDS), count)

    records: List[Dict[str, str]] = []
    for num in id_numbers:
        record: Dict[str, str] = {"application_id": _make_application_id(num)}
        for feature, values in FEATURES.items():
            record[feature] = rng.choice(values)
        records.append(record)
    return records


def generate_training(
    master: List[Dict[str, str]],
    count: int = 100,
    *,
    seed: int = 7,
    pool_size: Optional[int] = None,
    noise: float = 0.15,
) -> List[Dict[str, str]]:
    """Generate ``count`` labelled training observations from the ``master`` catalog.

    Records are drawn (with replacement) from a *pool* of master applications so
    that classes recur and the model has signal to learn. ``noise`` is the
    per-feature probability that a value is randomly resampled rather than copied
    from the application's canonical profile.

    Each row is ``{<feature>: <value>, ..., "application_id": <label>}``.
    """
    if not master:
        raise ValueError("master catalog is empty")
    if count <= 0:
        raise ValueError("count must be a positive integer")
    if not 0.0 <= noise <= 1.0:
        raise ValueError("noise must be between 0.0 and 1.0")

    rng = random.Random(seed)

    # Restrict to a learnable pool so labels repeat across the training set.
    if pool_size is None:
        pool_size = min(len(master), max(1, count // 3))
    pool_size = max(1, min(pool_size, len(master)))
    pool = master[:pool_size]

    records: List[Dict[str, str]] = []
    for _ in range(count):
        app = rng.choice(pool)
        record: Dict[str, str] = {}
        for feature in FEATURE_NAMES:
            if rng.random() < noise:
                record[feature] = rng.choice(FEATURES[feature])  # noisy observation
            else:
                record[feature] = app[feature]  # canonical value
        record["application_id"] = app["application_id"]
        records.append(record)
    return records

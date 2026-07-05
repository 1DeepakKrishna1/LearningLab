from app_detector.config import FEATURE_NAMES
from app_detector.datagen import generate_master, generate_training


def test_master_has_unique_ids_and_all_features():
    records = generate_master(count=200, seed=1)
    assert len(records) == 200
    ids = [r["application_id"] for r in records]
    assert len(set(ids)) == 200  # unique primary keys
    for r in records:
        assert r["application_id"].startswith("APP-")
        for f in FEATURE_NAMES:
            assert f in r and isinstance(r[f], str)


def test_master_is_deterministic_with_seed():
    assert generate_master(50, seed=5) == generate_master(50, seed=5)
    assert generate_master(50, seed=5) != generate_master(50, seed=6)


def test_training_labels_come_from_master_pool():
    master = generate_master(100, seed=2)
    training = generate_training(master, count=80, seed=3, pool_size=20, noise=0.1)
    assert len(training) == 80
    master_ids = {r["application_id"] for r in master[:20]}
    for row in training:
        assert row["application_id"] in master_ids
        for f in FEATURE_NAMES:
            assert f in row


def test_training_no_noise_matches_profile_exactly():
    master = generate_master(30, seed=4)
    training = generate_training(master, count=40, seed=9, pool_size=5, noise=0.0)
    by_id = {r["application_id"]: r for r in master}
    for row in training:
        profile = by_id[row["application_id"]]
        for f in FEATURE_NAMES:
            assert row[f] == profile[f]


def test_generate_master_validates_count():
    import pytest

    with pytest.raises(ValueError):
        generate_master(0)

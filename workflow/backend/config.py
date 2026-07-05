"""Profile-based data directory configuration."""
import os
from pathlib import Path

VALID_PROFILES = {"mock", "scratch", "dev", "test", "uat", "prod"}


def get_profile() -> str:
    profile = os.getenv("PROFILE", "mock").lower()
    if profile not in VALID_PROFILES:
        raise ValueError(f"Invalid PROFILE '{profile}'. Must be one of: {sorted(VALID_PROFILES)}")
    return profile


def get_data_dir() -> Path:
    """Return backend/AppData/{profile}/ and create it if missing."""
    data_dir = Path(__file__).parent / "AppData" / get_profile()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

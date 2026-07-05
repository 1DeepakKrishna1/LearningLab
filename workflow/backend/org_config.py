"""Organization branding/config derived from environment variables.

Configured via .env:
    ORG_NAME   – display name shown across the UI/API (default "Incepta")
    ORG_DOMAIN – email domain for login accounts (default derived from ORG_NAME)
    ORG_LOGO   – optional path to a logo image. If unset or invalid, no logo is shown.
"""
import os
import re
from pathlib import Path

_BACKEND_DIR = Path(__file__).parent

_ALLOWED_LOGO_EXT = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"}
_MEDIA_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml", ".gif": "image/gif", ".webp": "image/webp",
}

_DEFAULT_ORG_NAME = "Incepta"


def get_org_name() -> str:
    return os.getenv("ORG_NAME", "").strip() or _DEFAULT_ORG_NAME


def _slugify_domain(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", name.lower())
    return f"{slug or 'org'}.com"


def get_org_domain() -> str:
    """Email domain for org accounts; derived from ORG_NAME when not set explicitly."""
    domain = os.getenv("ORG_DOMAIN", "").strip().lstrip("@").lower()
    return domain or _slugify_domain(get_org_name())


def apply_org_domain(email: str) -> str:
    """Rewrite the domain part of an email to the configured org domain."""
    if not email or "@" not in email:
        return email
    local = email.split("@", 1)[0]
    return f"{local}@{get_org_domain()}"


def get_logo_path() -> Path | None:
    """Return a validated logo Path, or None if not configured / file is invalid."""
    raw = os.getenv("ORG_LOGO", "").strip()
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = (_BACKEND_DIR / p).resolve()
    if p.is_file() and p.suffix.lower() in _ALLOWED_LOGO_EXT:
        return p
    return None


def has_logo() -> bool:
    return get_logo_path() is not None


def get_logo_media_type() -> str | None:
    p = get_logo_path()
    return _MEDIA_TYPES.get(p.suffix.lower()) if p else None


def get_logo_version() -> str | None:
    """Cache-busting token derived from the logo file (size + mtime).

    Changes whenever the configured logo file changes, so clients fetch the new
    image instead of a stale cached one for the fixed /config/logo URL.
    """
    p = get_logo_path()
    if not p:
        return None
    st = p.stat()
    return f"{st.st_size}-{st.st_mtime_ns}"

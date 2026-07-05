"""Idempotent database seeder.

Creates roles + permissions, three demo users (admin/marketer/viewer), default
console provider configs, and loads sample contacts/templates/segments from
``data/sample-data``. Safe to run repeatedly.

Run with:  python -m app.seed
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import load_json_file
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    Consent,
    Contact,
    Permission,
    ProviderConfig,
    Role,
    Segment,
    Template,
    User,
)
from app.models.enums import Channel, ConsentStatus, ProviderType, RoleName

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.seed")

PERMISSIONS = [
    "campaign:read", "campaign:write", "campaign:approve",
    "template:read", "template:write",
    "contact:read", "contact:write",
    "segment:read", "segment:write",
    "provider:read", "provider:write",
    "analytics:read", "report:read", "report:write",
    "user:manage", "audit:read",
]

ROLE_PERMISSIONS = {
    RoleName.ADMIN.value: PERMISSIONS,
    RoleName.MARKETER.value: [
        "campaign:read", "campaign:write", "campaign:approve",
        "template:read", "template:write", "contact:read", "contact:write",
        "segment:read", "segment:write", "provider:read",
        "analytics:read", "report:read", "report:write",
    ],
    RoleName.VIEWER.value: [
        "campaign:read", "template:read", "contact:read", "segment:read",
        "provider:read", "analytics:read", "report:read",
    ],
}

DEMO_USERS = [
    ("admin@local", "Admin User", "Admin@123", [RoleName.ADMIN.value]),
    ("marketer@local", "Marketer User", "Marketer@123", [RoleName.MARKETER.value]),
    ("viewer@local", "Viewer User", "Viewer@123", [RoleName.VIEWER.value]),
]


def _seed_rbac(db: Session) -> dict[str, Role]:
    perms: dict[str, Permission] = {}
    for code in PERMISSIONS:
        perm = db.scalar(select(Permission).where(Permission.code == code))
        if not perm:
            perm = Permission(code=code, description=code.replace(":", " ").title())
            db.add(perm)
        perms[code] = perm
    db.flush()

    roles: dict[str, Role] = {}
    for role_name, perm_codes in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if not role:
            role = Role(name=role_name, description=f"{role_name.title()} role")
            db.add(role)
        role.permissions = [perms[c] for c in perm_codes]
        roles[role_name] = role
    db.flush()
    return roles


def _seed_users(db: Session, roles: dict[str, Role]) -> None:
    for email, name, password, role_names in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(email=email, full_name=name, hashed_password=hash_password(password))
            db.add(user)
        user.roles = [roles[r] for r in role_names]
    db.flush()


def _seed_providers(db: Session) -> None:
    defaults = [
        ("Console Email", Channel.EMAIL, ProviderType.CONSOLE),
        ("Console SMS", Channel.SMS, ProviderType.CONSOLE),
        ("Console Push", Channel.PUSH, ProviderType.CONSOLE),
    ]
    for name, channel, ptype in defaults:
        existing = db.scalar(select(ProviderConfig).where(ProviderConfig.name == name))
        if not existing:
            db.add(ProviderConfig(
                name=name, channel=channel.value, provider_type=ptype.value,
                config={}, mode="console", is_default=True, is_active=True,
            ))
    db.flush()


def _seed_templates(db: Session) -> None:
    data = load_json_file("sample-data/templates.json") or []
    for item in data:
        if db.scalar(select(Template).where(Template.name == item["name"])):
            continue
        db.add(Template(**item))
    db.flush()


def _seed_contacts(db: Session) -> None:
    data = load_json_file("sample-data/contacts.json") or []
    for item in data:
        email = item.get("email")
        if email and db.scalar(select(Contact).where(Contact.email == email)):
            continue
        contact = Contact(**item)
        db.add(contact)
        db.flush()
        # Default subscribed consent for email/sms.
        for ch in (Channel.EMAIL.value, Channel.SMS.value):
            db.add(Consent(contact_id=contact.id, channel=ch,
                           status=ConsentStatus.SUBSCRIBED.value, source="seed"))
    db.flush()


def _seed_segments(db: Session) -> None:
    data = load_json_file("sample-data/segments.json") or []
    for item in data:
        if db.scalar(select(Segment).where(Segment.name == item["name"])):
            continue
        db.add(Segment(name=item["name"], description=item.get("description", ""),
                       definition=item.get("definition", {}), is_dynamic=item.get("is_dynamic", True)))
    db.flush()


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        roles = _seed_rbac(db)
        _seed_users(db, roles)
        _seed_providers(db)
        _seed_templates(db)
        _seed_contacts(db)
        _seed_segments(db)
        db.commit()
        logger.info("Seed complete. Demo logins:")
        for email, _, password, _ in DEMO_USERS:
            logger.info("  %s / %s", email, password)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()

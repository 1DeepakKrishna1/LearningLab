"""Unit tests for RBAC."""
from app.domain.enums import Role
from app.security.jwt_handler import JwtError, JwtHandler
from app.security.passwords import hash_password, verify_password
from app.security.rbac import can, required_role


def test_role_hierarchy():
    assert Role.ADMIN.satisfies(Role.VIEWER)
    assert Role.DESIGNER.satisfies(Role.OPERATOR)
    assert not Role.VIEWER.satisfies(Role.OPERATOR)


def test_permission_matrix():
    assert can(Role.OPERATOR, "workflow:run")
    assert not can(Role.VIEWER, "workflow:run")
    assert can(Role.ADMIN, "user:manage")
    assert not can(Role.DESIGNER, "user:manage")
    assert required_role("unknown:permission") == Role.ADMIN  # fail closed


def test_password_hash_roundtrip():
    h = hash_password("s3cret")
    assert verify_password("s3cret", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip_and_tamper():
    jwt = JwtHandler("secret", expire_minutes=60)
    token = jwt.encode({"sub": "u1", "role": "admin"})
    assert jwt.decode(token)["sub"] == "u1"
    import pytest
    with pytest.raises(JwtError):
        jwt.decode(token + "tamper")

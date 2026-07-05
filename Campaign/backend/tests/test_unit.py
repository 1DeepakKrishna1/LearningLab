"""Unit tests for security, segment engine, template rendering, state machine."""
from __future__ import annotations

import pytest

from app.core.security import (
    ACCESS_TOKEN,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services import campaign_service as svc
from app.services import template_service


def test_password_hash_roundtrip():
    hashed = hash_password("S3cret!!")
    assert hashed != "S3cret!!"
    assert verify_password("S3cret!!", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_contains_roles():
    token = create_access_token("42", ["admin"])
    claims = decode_token(token)
    assert claims["sub"] == "42"
    assert claims["type"] == ACCESS_TOKEN
    assert claims["roles"] == ["admin"]


def test_template_variable_substitution_and_escaping():
    from app.models import Template

    tpl = Template(name="t", channel="email", subject="Hi {{first_name}}",
                   html_content="<p>{{first_name}}</p>")

    class FakeContact:
        email = "a@b.com"; phone = None; first_name = "<b>Al</b>"; last_name = "X"
        country = "US"; attributes = {}

    rendered = template_service.render_for_contact(tpl, FakeContact())
    assert rendered["subject"] == "Hi <b>Al</b>"
    # HTML body escapes the injected value (XSS mitigation).
    assert "&lt;b&gt;Al&lt;/b&gt;" in rendered["body"]


def test_sms_segment_count():
    assert template_service.sms_segment_count("a" * 10) == 1
    assert template_service.sms_segment_count("a" * 160) == 1
    assert template_service.sms_segment_count("a" * 161) == 2


def test_state_machine_transitions():
    assert svc.can_transition("draft", "pending_approval")
    assert not svc.can_transition("draft", "completed")
    assert svc.can_transition("approved", "scheduled")
    with pytest.raises(Exception):
        svc.assert_transition("completed", "sending")


def test_segment_engine_compiles(client_db_unused=None):
    from app.services import segment_engine

    definition = {"op": "AND", "rules": [{"field": "country", "operator": "eq", "value": "US"}]}
    clause = segment_engine.compile_rule_tree(definition)
    assert clause is not None

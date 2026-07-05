"""Template rendering and personalization.

Uses a safe ``{{ variable }}`` substitution (no arbitrary code execution).
Missing variables render as empty strings. Also computes SMS segment counts.
"""
from __future__ import annotations

import html
import math
import re
from typing import Any

from app.models import Contact, Template
from app.models.enums import Channel

_VAR_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*}}")


def contact_context(contact: Contact) -> dict[str, Any]:
    """Flatten a contact into a personalization context."""
    ctx: dict[str, Any] = {
        "email": contact.email or "",
        "phone": contact.phone or "",
        "first_name": contact.first_name or "",
        "last_name": contact.last_name or "",
        "country": contact.country or "",
    }
    for key, value in (contact.attributes or {}).items():
        ctx[key] = value
    return ctx


def render_string(template_text: str | None, context: dict[str, Any], *, escape: bool = False) -> str:
    if not template_text:
        return ""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        value = context.get(key, "")
        text = "" if value is None else str(value)
        return html.escape(text) if escape else text

    return _VAR_PATTERN.sub(_replace, template_text)


def extract_variables(template_text: str | None) -> list[str]:
    if not template_text:
        return []
    return sorted({m.group(1) for m in _VAR_PATTERN.finditer(template_text)})


def sms_segment_count(text: str) -> int:
    """GSM-7 segmentation heuristic: 160 chars single / 153 concatenated."""
    length = len(text)
    if length == 0:
        return 0
    if length <= 160:
        return 1
    return math.ceil(length / 153)


def render_for_contact(template: Template, contact: Contact) -> dict[str, Any]:
    """Render a template for a specific contact, channel-aware.

    Returns a dict with at minimum ``subject`` and ``body`` (HTML for email).
    """
    ctx = contact_context(contact)
    if template.channel == Channel.EMAIL.value:
        # Escape user-derived values in HTML to mitigate stored XSS in templates.
        return {
            "subject": render_string(template.subject, ctx),
            "body": render_string(template.html_content, ctx, escape=True),
            "preheader": render_string(template.preheader, ctx),
        }
    if template.channel == Channel.SMS.value:
        body = render_string(template.text_content, ctx)
        return {"subject": None, "body": body, "segments": sms_segment_count(body)}
    # Push
    return {
        "subject": render_string(template.title, ctx),
        "body": render_string(template.body, ctx),
        "image_url": template.image_url,
        "deep_link": template.deep_link,
        "buttons": template.buttons or [],
    }


def preview(template: Template, sample: dict[str, Any]) -> dict[str, Any]:
    """Render a template against arbitrary sample values (preview endpoint)."""
    if template.channel == Channel.EMAIL.value:
        body = render_string(template.html_content, sample, escape=True)
        return {"subject": render_string(template.subject, sample), "body": body}
    if template.channel == Channel.SMS.value:
        body = render_string(template.text_content, sample)
        return {"subject": None, "body": body, "sms_segments": sms_segment_count(body), "char_count": len(body)}
    body = render_string(template.body, sample)
    return {"subject": render_string(template.title, sample), "body": body}

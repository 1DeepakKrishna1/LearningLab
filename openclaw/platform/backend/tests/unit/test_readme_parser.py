"""Unit tests for the README parser."""
from app.registry.readme_parser import parse_readme

SAMPLE = """# Send Email

Composes and sends a new email through Outlook.

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| to | string or list | Yes | — | Recipient address(es). |
| subject | string | Yes | — | Subject line. |
| body | string | No | "" | Body of the email. |
| is_html | bool | No | false | HTML body flag. |

## Return Value

| Field | Type | Description |
|-------|------|-------------|
| status | string | "success" or "error" |
| data | string | Confirmation message. |

## Example

```json
{"to": "a@b.com", "subject": "Hi"}
```
"""


def test_parses_title_and_description():
    parsed = parse_readme(SAMPLE)
    assert parsed.display_name == "Send Email"
    assert "Outlook" in parsed.description


def test_parses_parameters_with_required_and_defaults():
    parsed = parse_readme(SAMPLE)
    by_name = {p["name"]: p for p in parsed.parameters}
    assert by_name["to"]["required"] is True
    assert by_name["body"]["required"] is False
    assert by_name["is_html"]["default"] is False
    assert set(by_name) == {"to", "subject", "body", "is_html"}


def test_parses_returns_and_examples():
    parsed = parse_readme(SAMPLE)
    assert {r["field"] for r in parsed.returns} == {"status", "data"}
    assert parsed.examples and parsed.examples[0]["to"] == "a@b.com"


def test_missing_sections_degrade_gracefully():
    parsed = parse_readme("# Title only\n\nJust a description.")
    assert parsed.display_name == "Title only"
    assert parsed.parameters == []
    assert parsed.returns == []

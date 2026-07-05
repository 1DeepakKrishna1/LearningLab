"""Segment engine: compile a JSON rule tree into SQLAlchemy filters.

Rule tree shape::

    {
      "op": "AND",            # AND | OR
      "rules": [
        {"field": "country", "operator": "eq", "value": "US"},
        {"field": "attributes.plan", "operator": "in", "value": ["pro", "ent"]},
        {"op": "OR", "rules": [ ... ]}      # nested group
      ]
    }

Supported fields: any scalar column on ``Contact`` (email, country, ...),
``tags`` (membership), and ``attributes.<key>`` (JSON attribute lookups).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import String, and_, func, not_, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import Contact

# Columns directly filterable on the Contact model.
_SCALAR_FIELDS = {
    "email": Contact.email,
    "phone": Contact.phone,
    "first_name": Contact.first_name,
    "last_name": Contact.last_name,
    "country": Contact.country,
    "timezone": Contact.timezone,
    "is_active": Contact.is_active,
}


class SegmentError(ValueError):
    """Raised for malformed segment definitions."""


def _scalar_condition(col: ColumnElement, operator: str, value: Any) -> ColumnElement:
    match operator:
        case "eq":
            return col == value
        case "ne":
            return col != value
        case "gt":
            return col > value
        case "gte":
            return col >= value
        case "lt":
            return col < value
        case "lte":
            return col <= value
        case "contains":
            return col.ilike(f"%{value}%")
        case "not_contains":
            return not_(col.ilike(f"%{value}%"))
        case "starts_with":
            return col.ilike(f"{value}%")
        case "ends_with":
            return col.ilike(f"%{value}")
        case "in":
            return col.in_(value if isinstance(value, list) else [value])
        case "not_in":
            return not_(col.in_(value if isinstance(value, list) else [value]))
        case "is_set":
            return col.is_not(None)
        case "is_not_set":
            return col.is_(None)
        case _:
            raise SegmentError(f"Unsupported operator '{operator}'")


def _attribute_condition(key: str, operator: str, value: Any) -> ColumnElement:
    """Filter on Contact.attributes JSON. SQLite-compatible via json_extract."""
    col = func.json_extract(Contact.attributes, f"$.{key}").cast(String)
    str_value = None if value is None else str(value)
    if operator in {"in", "not_in"} and isinstance(value, list):
        vals = [str(v) for v in value]
        return col.in_(vals) if operator == "in" else not_(col.in_(vals))
    if operator in {"is_set", "is_not_set"}:
        return col.is_not(None) if operator == "is_set" else col.is_(None)
    return _scalar_condition(col, operator, str_value)


def _tag_condition(operator: str, value: Any) -> ColumnElement:
    """Membership test against the tags JSON array (SQLite LIKE heuristic)."""
    needle = f'%"{value}"%'
    tags_text = func.coalesce(Contact.tags, "[]").cast(String)
    if operator in {"contains", "eq", "in"}:
        return tags_text.like(needle)
    if operator in {"not_contains", "ne", "not_in"}:
        return not_(tags_text.like(needle))
    raise SegmentError(f"Unsupported tag operator '{operator}'")


def _compile_condition(rule: dict[str, Any]) -> ColumnElement:
    field = rule.get("field")
    operator = rule.get("operator")
    value = rule.get("value")
    if not field or not operator:
        raise SegmentError("Condition requires 'field' and 'operator'")

    if field == "tags":
        return _tag_condition(operator, value)
    if field.startswith("attributes."):
        return _attribute_condition(field.split(".", 1)[1], operator, value)
    if field in _SCALAR_FIELDS:
        return _scalar_condition(_SCALAR_FIELDS[field], operator, value)
    raise SegmentError(f"Unknown field '{field}'")


def compile_rule_tree(node: dict[str, Any]) -> ColumnElement | None:
    """Recursively compile a rule tree into a single SQLAlchemy boolean clause."""
    if not node:
        return None
    # Leaf condition
    if "field" in node:
        return _compile_condition(node)

    op = (node.get("op") or "AND").upper()
    rules = node.get("rules") or []
    clauses = [compile_rule_tree(r) for r in rules]
    clauses = [c for c in clauses if c is not None]
    if not clauses:
        return None
    return and_(*clauses) if op == "AND" else or_(*clauses)


def build_query(definition: dict[str, Any]):
    """Return a SELECT for matching contacts (active only)."""
    stmt = select(Contact).where(Contact.is_active.is_(True))
    clause = compile_rule_tree(definition)
    if clause is not None:
        stmt = stmt.where(clause)
    return stmt


def evaluate(db: Session, definition: dict[str, Any]) -> list[Contact]:
    return list(db.scalars(build_query(definition)))


def count(db: Session, definition: dict[str, Any]) -> int:
    subq = build_query(definition).subquery()
    return db.scalar(select(func.count()).select_from(subq)) or 0

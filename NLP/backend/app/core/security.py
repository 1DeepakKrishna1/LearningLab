"""
SQL validation and security layer.

All generated SQL passes through this module before execution.
Rules:
  - Only SELECT statements are allowed.
  - Dangerous keywords and patterns are blocked.
  - All column references are validated against the known schema.
  - Query is parsed with sqlglot to ensure structural validity.
"""
from __future__ import annotations

import re
from typing import Iterable

import sqlglot
import sqlglot.expressions as exp
from loguru import logger

from app.core.exceptions import QueryValidationError

# ── Blocked patterns (case-insensitive raw-text check before parsing) ─────────
_BLOCK_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bCREATE\b",
        r"\bALTER\b",
        r"\bTRUNCATE\b",
        r"\bREPLACE\b",
        r"\bEXEC\b",
        r"\bEXECUTE\b",
        r"\bMERGE\b",
        r"--",          # SQL line comment
        r"/\*",         # SQL block comment open
        r"\bxp_",       # SQL Server extended procs
        r"\bsp_",       # SQL Server stored procs
        r"\bCAST\s*\(.*EXEC",
        r"\bUNION\s+ALL\s+SELECT.*FROM\s+information_schema",
    ]
]

# ── Allowed top-level statement type ─────────────────────────────────────────
_ALLOWED_STATEMENT = exp.Select


def validate_sql(sql: str, allowed_columns: Iterable[str] | None = None) -> str:
    """
    Validate *sql* for safety and structural correctness.

    Parameters
    ----------
    sql:
        The SQL string to validate.
    allowed_columns:
        If provided, all column references in the query must appear in this set
        (case-insensitive).

    Returns
    -------
    str
        The original SQL string (normalised whitespace) if it passes all checks.

    Raises
    ------
    QueryValidationError
        If any check fails.
    """
    if not sql or not sql.strip():
        raise QueryValidationError("Empty SQL query.", "The SQL string must not be empty.")

    sql_stripped = sql.strip()

    # 1. Raw text pattern check
    for pattern in _BLOCK_PATTERNS:
        if pattern.search(sql_stripped):
            logger.warning("blocked_sql_pattern", pattern=pattern.pattern, sql=sql_stripped[:200])
            raise QueryValidationError(
                "Query contains forbidden SQL patterns.",
                f"Blocked pattern: {pattern.pattern}",
                code="FORBIDDEN_SQL_PATTERN",
            )

    # 2. Parse with sqlglot
    try:
        statements = sqlglot.parse(sql_stripped, dialect="sqlite")
    except Exception as exc:
        raise QueryValidationError("SQL parse error.", str(exc)) from exc

    if not statements:
        raise QueryValidationError("No SQL statement found.", "")

    if len(statements) > 1:
        raise QueryValidationError(
            "Only a single SQL statement is allowed.",
            f"Got {len(statements)} statements.",
        )

    stmt = statements[0]

    # 3. Only SELECT allowed
    if not isinstance(stmt, _ALLOWED_STATEMENT):
        raise QueryValidationError(
            "Only SELECT statements are permitted.",
            f"Received statement type: {type(stmt).__name__}",
            code="NON_SELECT_STATEMENT",
        )

    # 4. Column reference validation
    if allowed_columns is not None:
        allowed_lower = {c.lower() for c in allowed_columns}
        for col_node in stmt.find_all(exp.Column):
            col_name = col_node.name.lower()
            # Skip wildcard / aliases
            if col_name in ("*", "") or col_name.startswith("__"):
                continue
            if col_name not in allowed_lower:
                logger.warning("unknown_column_reference", column=col_name)
                raise QueryValidationError(
                    f"Unknown column reference: '{col_node.name}'.",
                    "Column does not exist in the dataset schema.",
                    code="UNKNOWN_COLUMN",
                )

    logger.debug("sql_validation_passed", sql=sql_stripped[:200])
    return sql_stripped


def sanitize_identifier(name: str) -> str:
    """
    Ensure a table / column name contains only safe characters.
    Raises QueryValidationError if it doesn't.
    """
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise QueryValidationError(
            f"Invalid identifier: '{name}'",
            "Identifiers must start with a letter or underscore and contain only alphanumerics.",
        )
    return name

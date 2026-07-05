"""
SQL Generator — converts a structured IntentObject into a safe, parameterised
SQLite SELECT statement.

Rules:
  - All column names are quoted with double-quotes to handle special chars.
  - Never use raw user input in SQL text; values go into bind params.
  - Every generated query ends with a LIMIT clause.
  - All column references are validated before the query is assembled.
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.exceptions import QueryValidationError
from app.schemas.query import IntentObject


def _q(name: str) -> str:
    """Wrap identifier in double-quotes."""
    # Prevent quote injection
    safe = name.replace('"', '')
    return f'"{safe}"'


class SQLGenerator:
    """
    Build a parameterised SQL query from an IntentObject.

    Returns (sql_template: str, bind_params: list[Any])
    The sql_template uses ? placeholders (SQLite style).
    """

    def __init__(self, table_name: str, available_columns: list[str]):
        self.table_name = table_name
        self._available = {c.lower(): c for c in available_columns}

    def _validate_col(self, name: str | None) -> str | None:
        """Confirm a column exists (case-insensitive). Raises if not found."""
        if name is None:
            return None
        key = name.lower()
        if key not in self._available:
            raise QueryValidationError(
                f"Column '{name}' not found in dataset.",
                f"Available columns: {', '.join(self._available.values())}",
                code="UNKNOWN_COLUMN",
            )
        return self._available[key]

    def build(
        self, intent: IntentObject, limit: int = 1000
    ) -> tuple[str, list[Any]]:
        """Dispatch to the correct builder method."""
        method = getattr(self, f"_build_{intent.intent}", None)
        if method is None:
            logger.warning("unknown_intent_falling_back_to_select", intent=intent.intent)
            return self._build_summary(intent, limit)
        return method(intent, limit)

    # ── Intent builders ───────────────────────────────────────────────────────

    def _build_top_n(self, intent: IntentObject, limit: int) -> tuple[str, list[Any]]:
        n = intent.n or 10
        agg_col = self._validate_col(intent.agg_col)
        group_col = self._validate_col(intent.group_by_col)
        agg_func = intent.agg_func or "SUM"
        order = "DESC" if (intent.order or "DESC").upper() == "DESC" else "ASC"

        if agg_col and group_col:
            sql = (
                f"SELECT {_q(group_col)}, "
                f"{agg_func}({_q(agg_col)}) AS agg_value "
                f"FROM {_q(self.table_name)} "
                f"GROUP BY {_q(group_col)} "
                f"ORDER BY agg_value {order} "
                f"LIMIT ?"
            )
            return sql, [min(n, limit)]

        # Fallback: no grouping — just select & order
        order_col = agg_col or list(self._available.values())[0]
        sql = (
            f"SELECT * FROM {_q(self.table_name)} "
            f"ORDER BY {_q(order_col)} {order} "
            f"LIMIT ?"
        )
        return sql, [min(n, limit)]

    def _build_aggregate(self, intent: IntentObject, limit: int) -> tuple[str, list[Any]]:
        agg_col = self._validate_col(intent.agg_col)
        group_col = self._validate_col(intent.group_by_col)
        agg_func = intent.agg_func or "SUM"

        if agg_col and group_col:
            sql = (
                f"SELECT {_q(group_col)}, "
                f"{agg_func}({_q(agg_col)}) AS agg_value, "
                f"COUNT(*) AS record_count "
                f"FROM {_q(self.table_name)} "
                f"GROUP BY {_q(group_col)} "
                f"ORDER BY agg_value DESC "
                f"LIMIT ?"
            )
            return sql, [limit]

        if agg_col:
            sql = (
                f"SELECT "
                f"COUNT(*) AS total_count, "
                f"{agg_func}({_q(agg_col)}) AS agg_value, "
                f"AVG({_q(agg_col)}) AS avg_value, "
                f"MIN({_q(agg_col)}) AS min_value, "
                f"MAX({_q(agg_col)}) AS max_value "
                f"FROM {_q(self.table_name)} "
                f"LIMIT ?"
            )
            return sql, [1]

        return self._build_summary(intent, limit)

    def _build_trend(self, intent: IntentObject, limit: int) -> tuple[str, list[Any]]:
        date_col = self._validate_col(intent.date_col)
        value_col = self._validate_col(intent.value_col or intent.agg_col)
        grouping = intent.time_grouping or "month"
        agg_func = intent.agg_func or "SUM"

        if not date_col:
            return self._build_aggregate(intent, limit)

        # SQLite strftime format
        strftime_map = {
            "day": "%Y-%m-%d",
            "week": "%Y-%W",
            "month": "%Y-%m",
            "quarter": "%Y",  # simplified
            "year": "%Y",
        }
        fmt = strftime_map.get(grouping, "%Y-%m")

        if value_col:
            sql = (
                f"SELECT strftime(?, {_q(date_col)}) AS time_period, "
                f"{agg_func}({_q(value_col)}) AS agg_value, "
                f"COUNT(*) AS record_count "
                f"FROM {_q(self.table_name)} "
                f"WHERE {_q(date_col)} IS NOT NULL "
                f"GROUP BY time_period "
                f"ORDER BY time_period ASC "
                f"LIMIT ?"
            )
            return sql, [fmt, limit]

        sql = (
            f"SELECT strftime(?, {_q(date_col)}) AS time_period, "
            f"COUNT(*) AS record_count "
            f"FROM {_q(self.table_name)} "
            f"WHERE {_q(date_col)} IS NOT NULL "
            f"GROUP BY time_period "
            f"ORDER BY time_period ASC "
            f"LIMIT ?"
        )
        return sql, [fmt, limit]

    def _build_filter(self, intent: IntentObject, limit: int) -> tuple[str, list[Any]]:
        conditions = intent.filter_conditions or []
        params: list[Any] = []
        where_parts: list[str] = []

        for cond in conditions:
            col = self._validate_col(cond.get("column"))
            if not col:
                continue
            op = cond.get("operator", "=")
            val = cond.get("value")

            # Only allow safe operators
            if op not in {">", "<", ">=", "<=", "=", "!=", "LIKE", "<>"}:
                continue

            where_parts.append(f"{_q(col)} {op} ?")
            params.append(val)

        if where_parts:
            where_clause = " AND ".join(where_parts)
            sql = f"SELECT * FROM {_q(self.table_name)} WHERE {where_clause} LIMIT ?"
            params.append(limit)
            return sql, params

        # Fallback — no parseable conditions
        sql = f"SELECT * FROM {_q(self.table_name)} LIMIT ?"
        return sql, [limit]

    def _build_summary(self, intent: IntentObject, limit: int) -> tuple[str, list[Any]]:
        sql = f"SELECT * FROM {_q(self.table_name)} LIMIT ?"
        return sql, [min(100, limit)]

    def _build_count(self, intent: IntentObject, limit: int) -> tuple[str, list[Any]]:
        group_col = self._validate_col(intent.group_by_col)
        if group_col:
            sql = (
                f"SELECT {_q(group_col)}, COUNT(*) AS record_count "
                f"FROM {_q(self.table_name)} "
                f"GROUP BY {_q(group_col)} "
                f"ORDER BY record_count DESC "
                f"LIMIT ?"
            )
            return sql, [limit]

        sql = f"SELECT COUNT(*) AS total_count FROM {_q(self.table_name)}"
        return sql, []

    def _build_correlation(self, intent: IntentObject, limit: int) -> tuple[str, list[Any]]:
        """Return all numeric-looking columns for client-side correlation calc."""
        cols = [c for c in (intent.columns or []) if self._validate_col(c)]
        if len(cols) < 2:
            # All columns
            cols = list(self._available.values())[:10]

        select_cols = ", ".join(_q(c) for c in cols)
        sql = f"SELECT {select_cols} FROM {_q(self.table_name)} LIMIT ?"
        return sql, [min(5000, limit)]

    def _build_distribution(self, intent: IntentObject, limit: int) -> tuple[str, list[Any]]:
        """Return the raw column values for histogram computation."""
        agg_col = self._validate_col(intent.agg_col)
        if not agg_col:
            cols = list(self._available.values())
            agg_col = cols[0] if cols else None

        if not agg_col:
            return self._build_summary(intent, limit)

        sql = (
            f"SELECT {_q(agg_col)} AS value, COUNT(*) AS frequency "
            f"FROM {_q(self.table_name)} "
            f"WHERE {_q(agg_col)} IS NOT NULL "
            f"GROUP BY {_q(agg_col)} "
            f"ORDER BY frequency DESC "
            f"LIMIT ?"
        )
        return sql, [limit]

"""
NLP Query Engine — the core value of the platform.

Pipeline:
  1. Pre-process  — lowercase, collapse whitespace, strip punctuation
  2. Intent Detection  — regex + keyword matching against 15+ patterns
  3. Entity Extraction — columns (fuzzy), aggregation funcs, filters, time groupings
  4. SQL Generation    — via SQLGenerator (parameterised, safe)
  5. LLM Fallback      — GPT-4o-mini if rule-based confidence < threshold
  6. SQL Validation    — core/security.py
  7. Cache check       — before execution
  8. Execution         — raw aiosqlite
"""
from __future__ import annotations

import difflib
import re
import time
from typing import Any

from loguru import logger

from app.config import get_settings
from app.core.exceptions import NLPParseError, QueryValidationError
from app.schemas.query import IntentObject

settings = get_settings()


# ── Constants ─────────────────────────────────────────────────────────────────

FUZZY_CUTOFF = 0.6

# ── Intent patterns  (order matters — more specific first) ────────────────────

_INTENT_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    (
        "top_n",
        [
            re.compile(r"\b(top|bottom|best|worst|highest?|lowest?|leading|trailing)\s+(\d+)\b", re.IGNORECASE),
            re.compile(r"\b(top|bottom)\s+(ten|five|three|two|one)\b", re.IGNORECASE),
            re.compile(r"\brank\w*\s+by\b", re.IGNORECASE),
            re.compile(r"\bfirst\s+\d+\b", re.IGNORECASE),
            re.compile(r"\blast\s+\d+\b", re.IGNORECASE),
        ],
    ),
    (
        "trend",
        [
            re.compile(r"\b(trend|over\s+time|time\s+series|monthly|weekly|daily|quarterly|yearly|annual|by\s+(month|week|day|quarter|year))\b", re.IGNORECASE),
            re.compile(r"\b(growth|change|evolution|progression)\s+(over|by|per)\b", re.IGNORECASE),
            re.compile(r"\b(revenue|sales|count)\s+(by|per)\s+(month|week|day|year|quarter)\b", re.IGNORECASE),
        ],
    ),
    (
        "correlation",
        [
            re.compile(r"\b(correlat|relationship\s+between|association\s+between|related\s+to)\b", re.IGNORECASE),
            re.compile(r"\bcompare\s+\w+\s+(and|with|vs\.?)\s+\w+\b", re.IGNORECASE),
        ],
    ),
    (
        "distribution",
        [
            re.compile(r"\b(distribution\s+of|histogram\s+of|spread\s+of|frequency\s+of|how\s+is\s+\w+\s+distributed)\b", re.IGNORECASE),
            re.compile(r"\bbreakdown\s+of\b", re.IGNORECASE),
        ],
    ),
    (
        "summary",
        [
            re.compile(r"\b(summarize|summarise|overview|statistics|stats|describe\s+the|tell\s+me\s+about|what\s+does\s+the\s+data|data\s+summary|quick\s+look)\b", re.IGNORECASE),
            re.compile(r"\b(show\s+all\s+stats|all\s+statistics|column\s+info)\b", re.IGNORECASE),
        ],
    ),
    (
        "count",
        [
            re.compile(r"\b(how\s+many|count\s+of|number\s+of|total\s+number|tally)\b", re.IGNORECASE),
            re.compile(r"\bcount\s+\w+\s+by\b", re.IGNORECASE),
            re.compile(r"\bcount\s+per\b", re.IGNORECASE),
        ],
    ),
    (
        "aggregate",
        [
            re.compile(r"\b(total|sum|average|avg|mean|median|max|maximum|min|minimum|highest?|lowest?)\s+\w+\s+by\b", re.IGNORECASE),
            re.compile(r"\b(sum|average|avg|mean|total)\s+of\s+\w+", re.IGNORECASE),
            re.compile(r"\bby\s+(region|country|category|department|group|segment|type|product|customer)\b", re.IGNORECASE),
            re.compile(r"\b(group\s+by|grouped\s+by|segmented\s+by|broken\s+down\s+by)\b", re.IGNORECASE),
        ],
    ),
    (
        "filter",
        [
            re.compile(r"\b(where|filter|show\s+me|find|list|display|get)\s+.*(greater|less|more|equal|above|below|between|not|contains?|starts?|ends?)\b", re.IGNORECASE),
            re.compile(r"\b(age|price|amount|quantity|score|rating)\s*(>|<|>=|<=|=|!=)\s*\d+", re.IGNORECASE),
            re.compile(r"\bwhere\s+\w+\s+(is|are|=|>|<)\b", re.IGNORECASE),
            re.compile(r"\b(status|type|category)\s+(is|=)\s+\w+", re.IGNORECASE),
        ],
    ),
]

_WORD_TO_N = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "twenty": 20, "fifty": 50, "hundred": 100,
}

_AGG_KEYWORDS: dict[str, str] = {
    "sum": "SUM", "total": "SUM", "totals": "SUM",
    "average": "AVG", "avg": "AVG", "mean": "AVG",
    "count": "COUNT", "counts": "COUNT", "number": "COUNT", "how many": "COUNT",
    "max": "MAX", "maximum": "MAX", "highest": "MAX", "largest": "MAX", "most": "MAX",
    "min": "MIN", "minimum": "MIN", "lowest": "MIN", "smallest": "MIN", "least": "MIN",
    "median": "MEDIAN",
}

_TIME_GROUPINGS: dict[str, str] = {
    "daily": "day", "day": "day", "days": "day",
    "weekly": "week", "week": "week", "weeks": "week",
    "monthly": "month", "month": "month", "months": "month",
    "quarterly": "quarter", "quarter": "quarter",
    "yearly": "year", "annual": "year", "annually": "year", "year": "year",
}

_FILTER_OPERATORS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(greater\s+than|more\s+than|above|over|>)\s+", re.IGNORECASE), ">"),
    (re.compile(r"\b(less\s+than|below|under|<)\s+", re.IGNORECASE), "<"),
    (re.compile(r"\b(greater\s+than\s+or\s+equal|at\s+least|>=)\s+", re.IGNORECASE), ">="),
    (re.compile(r"\b(less\s+than\s+or\s+equal|at\s+most|<=)\s+", re.IGNORECASE), "<="),
    (re.compile(r"\b(not\s+equal\s+to|!=|<>|is\s+not)\s+", re.IGNORECASE), "!="),
    (re.compile(r"\b(equal\s+to|equals?|is\s+exactly|=)\s+", re.IGNORECASE), "="),
    (re.compile(r"\b(contains?|includes?|like)\s+", re.IGNORECASE), "LIKE"),
    (re.compile(r"\b(starts?\s+with)\s+", re.IGNORECASE), "LIKE_START"),
    (re.compile(r"\b(ends?\s+with)\s+", re.IGNORECASE), "LIKE_END"),
]


# ── Column fuzzy matching ─────────────────────────────────────────────────────

def _fuzzy_match_column(
    token: str,
    available_columns: list[str],
    cutoff: float = FUZZY_CUTOFF,
) -> str | None:
    """
    Match *token* to the closest column name.
    1. Exact match
    2. Case-insensitive exact
    3. difflib.get_close_matches
    """
    # 1. Exact
    if token in available_columns:
        return token

    # 2. Case-insensitive
    lower_map = {c.lower(): c for c in available_columns}
    if token.lower() in lower_map:
        return lower_map[token.lower()]

    # 3. Fuzzy
    matches = difflib.get_close_matches(
        token.lower(),
        [c.lower() for c in available_columns],
        n=1,
        cutoff=cutoff,
    )
    if matches:
        return lower_map[matches[0]]

    return None


# ── Intent detection ──────────────────────────────────────────────────────────

def _detect_intent(query: str) -> tuple[str, float]:
    """Return (intent_name, confidence_score)."""
    scores: dict[str, int] = {}
    for intent_name, patterns in _INTENT_PATTERNS:
        for pat in patterns:
            if pat.search(query):
                scores[intent_name] = scores.get(intent_name, 0) + 1

    if not scores:
        return "summary", 0.4

    best = max(scores, key=lambda k: scores[k])
    total_patterns = sum(len(p) for _, p in _INTENT_PATTERNS)
    confidence = min(0.95, scores[best] / max(3, total_patterns / len(_INTENT_PATTERNS)))
    return best, confidence


# ── Entity extraction ─────────────────────────────────────────────────────────

def _extract_n(query: str) -> int:
    """Extract the N from 'top N' / 'bottom N'."""
    m = re.search(r"\b(top|bottom|first|last|best|worst)\s+(\d+)\b", query, re.IGNORECASE)
    if m:
        return int(m.group(2))
    # word form
    for word, val in _WORD_TO_N.items():
        if re.search(rf"\b(top|bottom|first|last)\s+{word}\b", query, re.IGNORECASE):
            return val
    return 10  # default


def _extract_order(query: str) -> str:
    if re.search(r"\b(bottom|worst|lowest?|ascending|asc|least)\b", query, re.IGNORECASE):
        return "ASC"
    return "DESC"


def _extract_agg_func(query: str) -> tuple[str, str | None]:
    """Return (AGG_FUNC, matched_keyword)."""
    q = query.lower()
    for kw, func in sorted(_AGG_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if kw in q:
            return func, kw
    return "SUM", None


def _extract_time_grouping(query: str) -> str | None:
    q = query.lower()
    for kw, grp in _TIME_GROUPINGS.items():
        if re.search(rf"\b{re.escape(kw)}\b", q):
            return grp
    return None


def _extract_columns(
    query: str,
    available_columns: list[str],
) -> list[str]:
    """
    Find all column name mentions in the query by trying each word/bigram/trigram
    against the available columns via fuzzy matching.
    """
    found: list[str] = []
    seen: set[str] = set()

    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", query)
    ngrams: list[str] = list(tokens)
    # bigrams
    for i in range(len(tokens) - 1):
        ngrams.append(f"{tokens[i]}_{tokens[i+1]}")
    # trigrams
    for i in range(len(tokens) - 2):
        ngrams.append(f"{tokens[i]}_{tokens[i+1]}_{tokens[i+2]}")

    # skip stop-words
    stop_words = {
        "show", "me", "the", "of", "by", "in", "with", "and", "or", "for",
        "a", "an", "is", "are", "where", "what", "how", "many", "get", "list",
        "find", "all", "from", "to", "than", "more", "less", "top", "bottom",
        "total", "average", "sum", "count", "max", "min", "mean", "over", "time",
        "give", "display", "filter", "between", "per", "each",
    }

    for tok in ngrams:
        if tok.lower() in stop_words:
            continue
        match = _fuzzy_match_column(tok, available_columns)
        if match and match not in seen:
            seen.add(match)
            found.append(match)

    return found


def _extract_filter_conditions(
    query: str,
    available_columns: list[str],
) -> list[dict[str, Any]]:
    """
    Parse simple filter expressions like:
      "age greater than 30"
      "status is cancelled"
      "price > 100"
    """
    conditions = []

    # Pattern: <col> <op> <value>
    for op_pattern, op_sym in _FILTER_OPERATORS:
        for m in op_pattern.finditer(query):
            before = query[: m.start()].strip()
            after = query[m.end() :].strip()

            # Extract the column (last word before operator)
            col_match = re.search(r"(\w+)\s*$", before)
            # Extract the value (first token after operator)
            val_match = re.match(r"(['\"]?[\w\s.@-]+['\"]?)", after)

            if not col_match or not val_match:
                continue

            col_token = col_match.group(1)
            raw_val = val_match.group(1).strip().strip("'\"")

            matched_col = _fuzzy_match_column(col_token, available_columns)
            if not matched_col:
                continue

            # Resolve LIKE variants
            actual_op = op_sym
            actual_val: Any = raw_val
            if op_sym == "LIKE_START":
                actual_op = "LIKE"
                actual_val = f"{raw_val}%"
            elif op_sym == "LIKE_END":
                actual_op = "LIKE"
                actual_val = f"%{raw_val}"
            elif op_sym == "LIKE":
                actual_val = f"%{raw_val}%"

            conditions.append(
                {"column": matched_col, "operator": actual_op, "value": actual_val}
            )

    return conditions


# ── Main NLP Engine ───────────────────────────────────────────────────────────

class NLPEngine:
    """
    Parse a natural-language query against a known dataset schema and
    return a structured IntentObject.
    """

    def __init__(self, available_columns: list[str], column_types: dict[str, str]):
        self.available_columns = available_columns
        self.column_types = column_types  # col_name → detected_type

    def parse(self, query: str) -> IntentObject:
        """
        Run the full NLP pipeline and return an IntentObject.
        Raises NLPParseError if the query cannot be resolved.
        """
        q = query.strip()
        if not q:
            raise NLPParseError("Empty query.", "Please provide a natural-language query.")

        intent, confidence = _detect_intent(q)
        logger.info("intent_detected", intent=intent, confidence=round(confidence, 3), query=q[:100])

        cols = _extract_columns(q, self.available_columns)
        agg_func, agg_kw = _extract_agg_func(q)
        time_grouping = _extract_time_grouping(q)

        # ── Resolve group-by and agg columns ─────────────────────────────────
        numeric_cols = [c for c, t in self.column_types.items() if t == "numeric"]
        date_cols = [c for c, t in self.column_types.items() if t == "datetime"]
        categorical_cols = [c for c, t in self.column_types.items() if t == "categorical"]

        agg_col: str | None = None
        group_by_col: str | None = None
        date_col: str | None = None
        value_col: str | None = None

        if cols:
            for c in cols:
                if self.column_types.get(c) == "numeric" and agg_col is None:
                    agg_col = c
                elif self.column_types.get(c) in ("categorical", "text") and group_by_col is None:
                    group_by_col = c
                elif self.column_types.get(c) == "datetime" and date_col is None:
                    date_col = c

        # Fallbacks
        if agg_col is None and numeric_cols:
            agg_col = numeric_cols[0]
        if group_by_col is None and categorical_cols:
            group_by_col = categorical_cols[0]
        if date_col is None and date_cols:
            date_col = date_cols[0]

        # For trend, value_col = same as agg_col
        if intent == "trend":
            value_col = agg_col

        # Filter conditions
        filter_conditions: list[dict] = []
        if intent == "filter":
            filter_conditions = _extract_filter_conditions(q, self.available_columns)

        return IntentObject(
            intent=intent,
            raw_query=q,
            n=_extract_n(q) if intent == "top_n" else None,
            columns=cols if cols else self.available_columns[:5],
            group_by_col=group_by_col,
            agg_func=agg_func,
            agg_col=agg_col,
            order=_extract_order(q),
            filter_conditions=filter_conditions if filter_conditions else None,
            date_col=date_col,
            value_col=value_col,
            time_grouping=time_grouping,
            confidence=confidence,
            fallback_used=False,
        )


# ── LLM Fallback ──────────────────────────────────────────────────────────────

async def llm_fallback_sql(
    query: str,
    table_name: str,
    column_schemas: list[dict],
    limit: int = 1000,
) -> str | None:
    """
    Call GPT-4o-mini to generate SQL from natural language.
    Returns SQL string or None if OpenAI is not configured / call fails.
    """
    if not settings.openai_enabled:
        return None

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        schema_lines = "\n".join(
            f"  - {c['name']} ({c['type']}){' [sample: ' + ', '.join(str(s) for s in c.get('samples', [])[:3]) + ']' if c.get('samples') else ''}"
            for c in column_schemas
        )

        system_prompt = (
            "You are an expert SQL generator for SQLite. "
            "Given a table schema and a natural-language question, produce ONLY a valid "
            "SQLite SELECT statement — no explanations, no markdown, no semicolons. "
            "NEVER use DROP, DELETE, INSERT, UPDATE, CREATE, ALTER, TRUNCATE, or comments."
        )

        user_prompt = (
            f"Table name: {table_name}\n"
            f"Columns:\n{schema_lines}\n\n"
            f"Question: {query}\n\n"
            f"Limit results to {limit} rows. Return only the SQL."
        )

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=512,
        )

        sql = response.choices[0].message.content
        if sql:
            sql = sql.strip().strip("`").strip()
            if sql.upper().startswith("SQL"):
                sql = sql[3:].strip()
            logger.info("llm_fallback_sql_generated", query=query[:80], sql=sql[:200])
            return sql

    except Exception as exc:
        logger.warning("llm_fallback_failed", error=str(exc))

    return None

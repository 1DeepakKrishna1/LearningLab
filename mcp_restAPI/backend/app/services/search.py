"""Natural-language endpoint search over an operation catalog.

Uses a lightweight TF-style relevance score with field weighting. This keeps
search dependency-free and instant; it can be upgraded to embeddings by
swapping :func:`search_operations` for a vector similarity implementation.
"""
from __future__ import annotations

import re
from collections import Counter

from ..openapi.parser import ParsedSpec
from ..schemas import Operation

_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Words that carry little intent signal.
_STOPWORDS = {
    "the", "a", "an", "of", "to", "for", "and", "or", "in", "on", "with",
    "get", "please", "can", "you", "me", "my", "i", "is", "are", "all",
    "list", "show", "give", "want", "need", "find",
}


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def _operation_tokens(op: Operation) -> Counter[str]:
    """Build a weighted bag of tokens for an operation."""
    bag: Counter[str] = Counter()
    # Field weights reflect how indicative each field is of intent.
    for text, weight in (
        (op.operation_id.replace("_", " "), 3),
        (op.summary, 3),
        (op.path.replace("/", " ").replace("{", " ").replace("}", " "), 2),
        (" ".join(op.tags), 2),
        (op.description, 1),
        (" ".join(p.name for p in op.parameters), 1),
    ):
        for tok in _tokenize(text):
            bag[tok] += weight
    # The HTTP verb is a strong intent signal (create/delete/update/list).
    verb_hints = {
        "GET": ["get", "list", "fetch", "read", "retrieve", "search"],
        "POST": ["create", "add", "new", "make", "place", "submit"],
        "PUT": ["update", "replace", "set"],
        "PATCH": ["update", "modify", "change", "edit"],
        "DELETE": ["delete", "remove", "cancel"],
    }
    for hint in verb_hints.get(op.method, []):
        bag[hint] += 2
    return bag


def search_operations(
    parsed: ParsedSpec, query: str, limit: int = 8
) -> list[tuple[Operation, float]]:
    """Return up to ``limit`` operations ranked by relevance to ``query``."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        # No usable query -> return a stable prefix of the catalog.
        return [(op, 0.0) for op in parsed.operations[:limit]]

    scored: list[tuple[Operation, float]] = []
    for op in parsed.operations:
        bag = _operation_tokens(op)
        if not bag:
            continue
        score = 0.0
        for qt in query_tokens:
            score += bag.get(qt, 0)
            # Partial / prefix matches (e.g. "customers" vs "customer").
            if qt not in bag:
                for tok, w in bag.items():
                    if tok.startswith(qt) or qt.startswith(tok):
                        score += w * 0.5
                        break
        if score > 0:
            scored.append((op, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]

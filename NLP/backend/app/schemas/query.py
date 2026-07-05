"""
Pydantic schemas for NLP query requests and responses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NLPQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Natural-language query")
    dataset_id: str = Field(..., description="Target dataset UUID")
    limit: int = Field(default=1000, ge=1, le=10_000, description="Max rows to return")
    use_cache: bool = Field(default=True, description="Whether to use the query cache")


class IntentObject(BaseModel):
    """Structured representation of the parsed NLP intent."""
    intent: str
    raw_query: str
    # common fields — populated depending on intent type
    n: Optional[int] = None
    columns: Optional[List[str]] = None
    group_by_col: Optional[str] = None
    agg_func: Optional[str] = None
    agg_col: Optional[str] = None
    order: Optional[str] = "DESC"
    filter_conditions: Optional[List[Dict[str, Any]]] = None
    date_col: Optional[str] = None
    value_col: Optional[str] = None
    time_grouping: Optional[str] = None
    confidence: float = 1.0
    fallback_used: bool = False


class QueryResult(BaseModel):
    sql: str
    rows: List[Dict[str, Any]]
    row_count: int
    columns: List[str]
    execution_time_ms: float
    from_cache: bool = False
    intent: Optional[IntentObject] = None


class NLPQueryResponse(BaseModel):
    success: bool
    query: str
    dataset_id: str
    result: Optional[QueryResult] = None
    error: Optional[str] = None
    detail: Optional[str] = None
    code: Optional[str] = None

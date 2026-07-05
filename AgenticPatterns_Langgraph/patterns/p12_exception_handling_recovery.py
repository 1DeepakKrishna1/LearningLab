"""
Pattern 12: Exception Handling and Recovery
=============================================
Concept: Each node in a data pipeline can fail. The graph detects failures
through conditional edges, logs them, attempts recovery (retry with back-off,
fallback data, or graceful degradation), and continues the pipeline or ends
cleanly with a partial result.

Recovery strategies:
  - Retry      : re-run the same node (up to max_retries times)
  - Fallback   : substitute mock/cached data and continue
  - Degrade    : mark the step as failed but proceed with partial data
  - Abort      : if critical failure, emit a structured error report

Graph:  START → fetch_data → [error?] → handle_fetch_error
                                              ↓ retry or fallback
              → transform_data → [error?] → handle_transform_error
              → analyze_data
              → generate_report → END

Demo:   Multi-stage pipeline with simulated failures to showcase all recovery paths.
"""
from __future__ import annotations

import random
import traceback as tb_module
from typing import Annotated, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

MAX_RETRIES = 2

# Failure injection controls (deterministic for demo reproducibility)
INJECT_FETCH_FAILURE_ON_ATTEMPT = 1     # fail the first fetch attempt
INJECT_TRANSFORM_FAILURE_ON_ATTEMPT = 1  # fail the first transform attempt


class RecoveryState(TypedDict):
    pipeline_input: str
    fetched_data: str
    transformed_data: str
    analysis: str
    report: str
    error_log: Annotated[List[Dict], operator.add]
    retry_counts: Dict[str, int]
    current_step: str
    fallback_used: Dict[str, bool]
    final_status: str          # "success" | "partial" | "degraded" | "failed"


class PatternExceptionHandlingRecovery(BasePattern):
    PATTERN_NUMBER = 12
    PATTERN_NAME = "Exception Handling and Recovery"
    DESCRIPTION = (
        "Detect node failures, retry with back-off, use fallbacks, and degrade gracefully."
    )

    # ------------------------------------------------------------------ nodes

    def _fetch_data(self, state: RecoveryState) -> dict:
        attempt = state["retry_counts"].get("fetch", 0) + 1
        # Inject failure on the first attempt only
        if attempt <= INJECT_FETCH_FAILURE_ON_ATTEMPT:
            return {
                "current_step": "fetch_failed",
                "retry_counts": {**state["retry_counts"], "fetch": attempt},
                "error_log": [{
                    "step": "fetch_data",
                    "attempt": attempt,
                    "error": "SimulatedTimeoutError: remote API did not respond within 5s",
                    "timestamp": "2025-03-14T10:00:00Z",
                }],
            }
        # Success path
        data = (
            "SALES_DATA_Q1_2025:\n"
            "Region,Revenue,Units\nNorth,1200000,4500\nSouth,980000,3800\n"
            "East,1450000,5200\nWest,760000,2900\n"
        )
        return {
            "fetched_data": data,
            "current_step": "fetch_ok",
            "retry_counts": {**state["retry_counts"], "fetch": attempt},
        }

    def _handle_fetch_error(self, state: RecoveryState) -> dict:
        retries = state["retry_counts"].get("fetch", 0)
        if retries < MAX_RETRIES:
            # Will retry
            return {
                "current_step": "fetch_retry",
                "error_log": [{
                    "step": "handle_fetch_error",
                    "action": f"scheduling_retry_{retries + 1}_of_{MAX_RETRIES}",
                }],
            }
        # Max retries exceeded — use fallback cached data
        fallback_data = (
            "SALES_DATA_CACHED_2024:\n"
            "Region,Revenue,Units\nNorth,1100000,4200\nSouth,920000,3600\n"
            "East,1350000,5000\nWest,720000,2750\n"
        )
        return {
            "fetched_data": fallback_data,
            "current_step": "fetch_fallback",
            "fallback_used": {**state["fallback_used"], "fetch": True},
            "error_log": [{
                "step": "handle_fetch_error",
                "action": "using_cached_fallback_data",
                "data_age": "~1 year old",
            }],
        }

    def _route_after_fetch(self, state: RecoveryState) -> str:
        step = state["current_step"]
        if step in ("fetch_ok", "fetch_fallback"):
            return "transform"
        return "retry_fetch"

    def _transform_data(self, state: RecoveryState) -> dict:
        attempt = state["retry_counts"].get("transform", 0) + 1
        # Inject parse failure on first attempt
        if attempt <= INJECT_TRANSFORM_FAILURE_ON_ATTEMPT:
            return {
                "current_step": "transform_failed",
                "retry_counts": {**state["retry_counts"], "transform": attempt},
                "error_log": [{
                    "step": "transform_data",
                    "attempt": attempt,
                    "error": "SimulatedParseError: malformed CSV at row 3",
                }],
            }
        # Success path — enrich CSV with derived fields
        raw = state["fetched_data"]
        all_lines = [l for l in raw.strip().split("\n") if l]
        # Find the CSV header row (contains "Region" and "Revenue")
        header_idx = next(
            (i for i, l in enumerate(all_lines) if "Region" in l and "Revenue" in l), 1
        )
        header_line = all_lines[header_idx]
        enriched = header_line + ",MarketShare\n"
        data_lines = [l.split(",") for l in all_lines[header_idx + 1:]]
        total_rev = sum(
            float(l[1]) for l in data_lines
            if len(l) >= 2 and l[1].strip().replace(".", "", 1).lstrip("-").isdigit()
        ) or 1.0
        for parts in data_lines:
            if len(parts) >= 2:
                try:
                    share = float(parts[1]) / total_rev * 100
                    enriched += ",".join(parts) + f",{share:.1f}%\n"
                except (ValueError, ZeroDivisionError):
                    pass
        return {
            "transformed_data": enriched,
            "current_step": "transform_ok",
            "retry_counts": {**state["retry_counts"], "transform": attempt},
        }

    def _handle_transform_error(self, state: RecoveryState) -> dict:
        retries = state["retry_counts"].get("transform", 0)
        if retries < MAX_RETRIES:
            return {
                "current_step": "transform_retry",
                "error_log": [{"step": "handle_transform_error", "action": f"retry_{retries + 1}"}],
            }
        # Degrade: use raw untransformed data
        return {
            "transformed_data": state["fetched_data"],
            "current_step": "transform_degraded",
            "fallback_used": {**state["fallback_used"], "transform": True},
            "error_log": [{
                "step": "handle_transform_error",
                "action": "degraded_to_raw_data",
                "note": "analysis may be less accurate",
            }],
        }

    def _route_after_transform(self, state: RecoveryState) -> str:
        step = state["current_step"]
        if step in ("transform_ok", "transform_degraded"):
            return "analyze"
        return "retry_transform"

    def _analyze_data(self, state: RecoveryState) -> dict:
        prompt = (
            "Analyse the following sales data and provide:\n"
            "1. Top performing region\n"
            "2. Revenue trends\n"
            "3. One actionable recommendation\n\n"
            f"Data:\n{state['transformed_data']}\n\n"
            "Keep the analysis concise (≤150 words)."
        )
        analysis = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=300)
        return {"analysis": analysis, "current_step": "analysis_ok"}

    def _generate_report(self, state: RecoveryState) -> dict:
        fallbacks = [k for k, v in state["fallback_used"].items() if v]
        warnings = (
            f"\n\n[WARNING] Fallback data used for: {', '.join(fallbacks)}"
            if fallbacks else ""
        )
        errors_summary = f"\nErrors encountered: {len(state['error_log'])}"

        report = (
            f"# Pipeline Report: {state['pipeline_input']}\n\n"
            f"## Analysis\n{state['analysis']}\n\n"
            f"## Pipeline Diagnostics{errors_summary}"
            f"{warnings}"
        )
        status = "success" if not fallbacks else ("partial" if len(fallbacks) < 2 else "degraded")
        return {"report": report, "final_status": status}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(RecoveryState)

        graph.add_node("fetch_data", self._fetch_data)
        graph.add_node("handle_fetch_error", self._handle_fetch_error)
        graph.add_node("transform_data", self._transform_data)
        graph.add_node("handle_transform_error", self._handle_transform_error)
        graph.add_node("analyze_data", self._analyze_data)
        graph.add_node("generate_report", self._generate_report)

        graph.add_edge(START, "fetch_data")
        graph.add_conditional_edges(
            "fetch_data",
            lambda s: "error" if s["current_step"] == "fetch_failed" else "ok",
            {"error": "handle_fetch_error", "ok": "transform_data"},
        )
        graph.add_conditional_edges(
            "handle_fetch_error",
            self._route_after_fetch,
            {"retry_fetch": "fetch_data", "transform": "transform_data"},
        )
        graph.add_conditional_edges(
            "transform_data",
            lambda s: "error" if s["current_step"] == "transform_failed" else "ok",
            {"error": "handle_transform_error", "ok": "analyze_data"},
        )
        graph.add_conditional_edges(
            "handle_transform_error",
            self._route_after_transform,
            {"retry_transform": "transform_data", "analyze": "analyze_data"},
        )
        graph.add_edge("analyze_data", "generate_report")
        graph.add_edge("generate_report", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: RecoveryState = {
                "pipeline_input": input_data,
                "fetched_data": "",
                "transformed_data": "",
                "analysis": "",
                "report": "",
                "error_log": [],
                "retry_counts": {},
                "current_step": "",
                "fallback_used": {},
                "final_status": "",
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["report"],
                elapsed_ms=elapsed_ms,
                steps=final["error_log"],
                metadata={
                    "final_status": final["final_status"],
                    "fallbacks_used": final["fallback_used"],
                    "retry_counts": final["retry_counts"],
                    "total_errors_handled": len(final["error_log"]),
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=tb_module.format_exc(),
            )

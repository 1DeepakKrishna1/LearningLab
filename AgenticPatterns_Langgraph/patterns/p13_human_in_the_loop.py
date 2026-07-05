"""
Pattern 13: Human-in-the-Loop (HITL)
======================================
Concept: The agent pauses at designated checkpoints to request human approval
or edits before proceeding. LangGraph's interrupt() mechanism suspends the
graph; execution resumes when the human provides input.

In INTERACTIVE mode (INTERACTIVE_HITL=true in .env):
  The graph uses interrupt() and resumes via graph.invoke() with a Command.

In DEMO mode (default):
  Pre-seeded human responses are injected so the demo runs non-interactively
  while still showing the full HITL state machine and approval trail.

Graph:  START → draft_subject → checkpoint_subject → draft_body
              → checkpoint_body → compile_recipients
              → checkpoint_recipients → finalize_email → END

Demo:   Draft a professional email: "Schedule a Q2 planning meeting with the
        engineering team for next Monday."
"""
from __future__ import annotations

import os
import traceback
from typing import Annotated, Any, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

INTERACTIVE = os.getenv("INTERACTIVE_HITL", "false").lower() == "true"


class HITLState(TypedDict):
    email_brief: str
    draft_subject: str
    draft_body: str
    recipients: List[str]
    # Human edits (populated by checkpoints)
    approved_subject: str
    approved_body: str
    approved_recipients: List[str]
    # Audit trail
    audit_trail: Annotated[List[Dict], operator.add]
    final_email: Dict[str, Any]
    # Pre-seeded human responses for demo mode
    demo_subject_edit: str
    demo_body_edit: str
    demo_recipients_edit: List[str]


class PatternHumanInTheLoop(BasePattern):
    PATTERN_NUMBER = 13
    PATTERN_NAME = "Human-in-the-Loop"
    DESCRIPTION = (
        "Graph pauses at checkpoints for human review/edit before proceeding."
    )

    # ------------------------------------------------------------------ nodes

    def _draft_subject(self, state: HITLState) -> dict:
        prompt = (
            f"Write a concise, professional email subject line for this brief:\n"
            f"{state['email_brief']}\n\n"
            "Return only the subject line, no quotes, no explanation."
        )
        subject = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=60)
        subject = subject.strip().strip('"').strip("'")
        return {
            "draft_subject": subject,
            "audit_trail": [{"checkpoint": "subject_drafted", "value": subject}],
        }

    def _checkpoint_subject(self, state: HITLState) -> dict:
        """HITL checkpoint: human reviews/edits the subject line."""
        if INTERACTIVE:
            from langgraph.types import interrupt
            human_input = interrupt({
                "message": "Review the email subject. Return approved text or edit it.",
                "current_value": state["draft_subject"],
            })
            approved = human_input if isinstance(human_input, str) else state["draft_subject"]
        else:
            # Demo mode: use pre-seeded edit (or approve as-is)
            approved = state["demo_subject_edit"] or state["draft_subject"]

        return {
            "approved_subject": approved,
            "audit_trail": [{
                "checkpoint": "subject_approved",
                "original": state["draft_subject"],
                "approved": approved,
                "edited": approved != state["draft_subject"],
                "mode": "interactive" if INTERACTIVE else "demo_auto",
            }],
        }

    def _draft_body(self, state: HITLState) -> dict:
        prompt = (
            f"Write a professional, friendly email body for the following brief:\n"
            f"{state['email_brief']}\n\n"
            f"Subject: {state['approved_subject']}\n\n"
            "Include: opening, key details, action items, and a professional closing. ~150 words."
        )
        body = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=400)
        return {
            "draft_body": body,
            "audit_trail": [{"checkpoint": "body_drafted", "length": len(body)}],
        }

    def _checkpoint_body(self, state: HITLState) -> dict:
        """HITL checkpoint: human reviews/edits the email body."""
        if INTERACTIVE:
            from langgraph.types import interrupt
            human_input = interrupt({
                "message": "Review the email body. Return approved text or provide edits.",
                "current_value": state["draft_body"],
            })
            approved = human_input if isinstance(human_input, str) else state["draft_body"]
        else:
            approved = state["demo_body_edit"] or state["draft_body"]

        return {
            "approved_body": approved,
            "audit_trail": [{
                "checkpoint": "body_approved",
                "edited": approved != state["draft_body"],
                "mode": "interactive" if INTERACTIVE else "demo_auto",
            }],
        }

    def _compile_recipients(self, state: HITLState) -> dict:
        prompt = (
            f"Based on this email brief, suggest 3 recipients (fictional names and emails):\n"
            f"{state['email_brief']}\n\n"
            "Return as a comma-separated list of 'Name <email@example.com>' entries. "
            "Nothing else."
        )
        raw = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=100)
        recipients = [r.strip() for r in raw.split(",") if r.strip()][:3]
        return {
            "recipients": recipients,
            "audit_trail": [{"checkpoint": "recipients_compiled", "recipients": recipients}],
        }

    def _checkpoint_recipients(self, state: HITLState) -> dict:
        """HITL checkpoint: human reviews/edits the recipient list."""
        if INTERACTIVE:
            from langgraph.types import interrupt
            human_input = interrupt({
                "message": "Review the recipient list. Approve or provide new list.",
                "current_value": state["recipients"],
            })
            approved = human_input if isinstance(human_input, list) else state["recipients"]
        else:
            approved = state["demo_recipients_edit"] or state["recipients"]

        return {
            "approved_recipients": approved,
            "audit_trail": [{
                "checkpoint": "recipients_approved",
                "edited": approved != state["recipients"],
                "mode": "interactive" if INTERACTIVE else "demo_auto",
            }],
        }

    def _finalize_email(self, state: HITLState) -> dict:
        final = {
            "subject": state["approved_subject"],
            "body": state["approved_body"],
            "recipients": state["approved_recipients"],
            "audit_trail_length": len(state["audit_trail"]),
            "fully_human_approved": True,
        }
        return {
            "final_email": final,
            "audit_trail": [{"checkpoint": "email_finalized", "status": "ready_to_send"}],
        }

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(HITLState)

        graph.add_node("draft_subject", self._draft_subject)
        graph.add_node("checkpoint_subject", self._checkpoint_subject)
        graph.add_node("draft_body", self._draft_body)
        graph.add_node("checkpoint_body", self._checkpoint_body)
        graph.add_node("compile_recipients", self._compile_recipients)
        graph.add_node("checkpoint_recipients", self._checkpoint_recipients)
        graph.add_node("finalize_email", self._finalize_email)

        graph.add_edge(START, "draft_subject")
        graph.add_edge("draft_subject", "checkpoint_subject")
        graph.add_edge("checkpoint_subject", "draft_body")
        graph.add_edge("draft_body", "checkpoint_body")
        graph.add_edge("checkpoint_body", "compile_recipients")
        graph.add_edge("compile_recipients", "checkpoint_recipients")
        graph.add_edge("checkpoint_recipients", "finalize_email")
        graph.add_edge("finalize_email", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: HITLState = {
                "email_brief": input_data,
                "draft_subject": "",
                "draft_body": "",
                "recipients": [],
                "approved_subject": "",
                "approved_body": "",
                "approved_recipients": [],
                "audit_trail": [],
                "final_email": {},
                # Demo mode pre-seeded edits (empty = auto-approve as-is)
                "demo_subject_edit": kwargs.get("demo_subject_edit", ""),
                "demo_body_edit": kwargs.get("demo_body_edit", ""),
                "demo_recipients_edit": kwargs.get("demo_recipients_edit", []),
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["final_email"],
                elapsed_ms=elapsed_ms,
                steps=final["audit_trail"],
                metadata={
                    "interactive_mode": INTERACTIVE,
                    "checkpoints": 3,
                    "edits_made": sum(1 for a in final["audit_trail"] if a.get("edited")),
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )

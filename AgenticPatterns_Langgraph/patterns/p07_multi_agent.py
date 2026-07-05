"""
Pattern 07: Multi-Agent
=======================
Concept: Multiple specialised agents collaborate under a supervisor. Each agent
has a distinct role (Researcher, Writer, Critic, Editor). The supervisor decides
which agent to activate next and when the work is complete.

Graph:  START → supervisor → [researcher | writer | critic | editor]
                    ↑               |
                    └───────────────┘  (agents always return to supervisor)
        supervisor → END  (when done)

Demo:   "Create a comprehensive market research report on the rise of AI coding
         assistants — trends, key players, user adoption, and future outlook."
"""
from __future__ import annotations

import traceback
from typing import Annotated, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

MAX_AGENT_TURNS = 6   # prevent infinite loops


class MultiAgentState(TypedDict):
    task: str
    next_agent: str          # "researcher" | "writer" | "critic" | "editor" | "done"
    research_notes: str
    draft_report: str
    critique: str
    final_report: str
    agent_log: Annotated[List[Dict], operator.add]
    turn: int


AGENT_SYSTEM_PROMPTS: Dict[str, str] = {
    "researcher": (
        "You are a rigorous market researcher. Gather and organise factual information, "
        "statistics, and trends. Output structured research notes with headers and bullet points."
    ),
    "writer": (
        "You are a professional business report writer. Transform research notes into "
        "a polished, well-structured report with executive summary, sections, and conclusions."
    ),
    "critic": (
        "You are a strict editor and fact-checker. Review the draft report for accuracy, "
        "logical gaps, unclear language, and missing evidence. List specific improvements needed."
    ),
    "editor": (
        "You are a copy editor. Polish the final draft for grammar, flow, professional tone, "
        "and conciseness. Produce the final publication-ready version."
    ),
}


class PatternMultiAgent(BasePattern):
    PATTERN_NUMBER = 7
    PATTERN_NAME = "Multi-Agent"
    DESCRIPTION = (
        "Supervisor orchestrates specialised agents (Researcher, Writer, Critic, Editor)."
    )

    # ------------------------------------------------------------------ nodes

    def _supervisor(self, state: MultiAgentState) -> dict:
        # Determine which agent to activate next based on current state
        has_research = bool(state["research_notes"])
        has_draft = bool(state["draft_report"])
        has_critique = bool(state["critique"])
        turn = state["turn"]

        if turn >= MAX_AGENT_TURNS:
            next_a = "done"
        elif not has_research:
            next_a = "researcher"
        elif not has_draft:
            next_a = "writer"
        elif not has_critique and not state["final_report"]:
            next_a = "critic"
        elif has_critique and not state["final_report"]:
            next_a = "editor"
        else:
            next_a = "done"

        return {
            "next_agent": next_a,
            "agent_log": [{"turn": turn, "supervisor_decision": next_a}],
        }

    def _route_supervisor(self, state: MultiAgentState) -> str:
        return state["next_agent"]

    def _researcher(self, state: MultiAgentState) -> dict:
        prompt = (
            f"Task: {state['task']}\n\n"
            "Conduct thorough market research. Provide:\n"
            "1. Market overview and size\n"
            "2. Key trends (3-4 bullet points)\n"
            "3. Major players and their positioning\n"
            "4. User adoption patterns\n"
            "5. Future outlook (18-month horizon)\n"
            "Use specific data points where possible."
        )
        notes = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=AGENT_SYSTEM_PROMPTS["researcher"],
            model=MODEL_LARGE,
            max_tokens=800,
        )
        return {
            "research_notes": notes,
            "turn": state["turn"] + 1,
            "agent_log": [{"turn": state["turn"], "agent": "researcher", "output_len": len(notes)}],
        }

    def _writer(self, state: MultiAgentState) -> dict:
        prompt = (
            f"Task: {state['task']}\n\n"
            f"Research notes:\n{state['research_notes']}\n\n"
            "Write a professional market research report (~400 words) with: "
            "Executive Summary, Market Landscape, Key Players, Adoption Trends, "
            "Future Outlook, and Recommendations."
        )
        draft = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=AGENT_SYSTEM_PROMPTS["writer"],
            model=MODEL_LARGE,
            max_tokens=900,
        )
        return {
            "draft_report": draft,
            "turn": state["turn"] + 1,
            "agent_log": [{"turn": state["turn"], "agent": "writer", "output_len": len(draft)}],
        }

    def _critic(self, state: MultiAgentState) -> dict:
        prompt = (
            f"Draft report to review:\n{state['draft_report']}\n\n"
            "Provide specific, actionable critique. List issues under:\n"
            "- Factual gaps or unsupported claims\n"
            "- Structural weaknesses\n"
            "- Missing key topics\n"
            "- Unclear or weak language\n"
            "Be concise but specific."
        )
        critique = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=AGENT_SYSTEM_PROMPTS["critic"],
            model=MODEL_LARGE,
            max_tokens=500,
        )
        return {
            "critique": critique,
            "turn": state["turn"] + 1,
            "agent_log": [{"turn": state["turn"], "agent": "critic", "output_len": len(critique)}],
        }

    def _editor(self, state: MultiAgentState) -> dict:
        prompt = (
            f"Original draft:\n{state['draft_report']}\n\n"
            f"Critique to address:\n{state['critique']}\n\n"
            "Produce the final, polished version of the report. Address all critique "
            "points. Ensure professional tone, clear structure, and strong conclusions."
        )
        final = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=AGENT_SYSTEM_PROMPTS["editor"],
            model=MODEL_LARGE,
            max_tokens=1000,
        )
        return {
            "final_report": final,
            "turn": state["turn"] + 1,
            "agent_log": [{"turn": state["turn"], "agent": "editor", "output_len": len(final)}],
        }

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(MultiAgentState)

        graph.add_node("supervisor", self._supervisor)
        graph.add_node("researcher", self._researcher)
        graph.add_node("writer", self._writer)
        graph.add_node("critic", self._critic)
        graph.add_node("editor", self._editor)

        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self._route_supervisor,
            {
                "researcher": "researcher",
                "writer": "writer",
                "critic": "critic",
                "editor": "editor",
                "done": END,
            },
        )
        for agent in ("researcher", "writer", "critic", "editor"):
            graph.add_edge(agent, "supervisor")

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: MultiAgentState = {
                "task": input_data,
                "next_agent": "",
                "research_notes": "",
                "draft_report": "",
                "critique": "",
                "final_report": "",
                "agent_log": [],
                "turn": 0,
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            output = final["final_report"] or final["draft_report"] or final["research_notes"]
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=output,
                elapsed_ms=elapsed_ms,
                steps=final["agent_log"],
                metadata={
                    "total_turns": final["turn"],
                    "agents_activated": list({log["agent"] for log in final["agent_log"] if "agent" in log}),
                    "has_critique": bool(final["critique"]),
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )

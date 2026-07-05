"""
Pattern 08: Memory Management
==============================
Concept: Demonstrates three memory tiers:
  1. Short-term (in-context) — the rolling conversation window.
  2. Long-term (persistent store) — extracted key facts stored across turns.
  3. Episodic summary — compresses old turns to free context budget.

Graph:  START → retrieve_memory → generate_response → update_memory
                                                            |
                                                    summarize_if_needed → END

The graph is invoked once per turn; the `long_term_memory` dict is passed
in the initial state and mutated, simulating persistence across calls.

Demo:   4-turn conversation about a fictional person named "Alex Chen"
        where facts introduced in turn 1 must be recalled in turns 3 and 4.
"""
from __future__ import annotations

import json
import re
import traceback
from typing import Annotated, Any, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

CONTEXT_WINDOW = 6      # max recent messages kept in short-term
SUMMARY_THRESHOLD = 4   # summarise when more than N messages exist


class MemoryState(TypedDict):
    user_input: str
    conversation_history: Annotated[List[Dict[str, str]], operator.add]
    long_term_memory: Dict[str, Any]    # key-value fact store
    retrieved_context: str
    response: str
    memory_summary: str
    turn_count: int


class PatternMemoryManagement(BasePattern):
    PATTERN_NUMBER = 8
    PATTERN_NAME = "Memory Management"
    DESCRIPTION = (
        "Three-tier memory: short-term (window), long-term (fact store), episodic (summary)."
    )

    # ------------------------------------------------------------------ nodes

    def _retrieve_memory(self, state: MemoryState) -> dict:
        """Pull relevant facts from long-term memory for the current query."""
        ltm = state["long_term_memory"]
        if not ltm:
            return {"retrieved_context": ""}

        if not state["user_input"]:
            return {"retrieved_context": ""}

        query_words = set(state["user_input"].lower().split())
        relevant: List[str] = []
        for key, value in ltm.items():
            key_words = set(key.lower().split("_"))
            if query_words & key_words:
                relevant.append(f"[memory] {key}: {value}")

        if not relevant:
            # Return the 3 most recent facts anyway
            recent_facts = list(ltm.items())[-3:]
            relevant = [f"[memory] {k}: {v}" for k, v in recent_facts]

        return {"retrieved_context": "\n".join(relevant)}

    def _generate_response(self, state: MemoryState) -> dict:
        """Build the prompt from all memory tiers and call the LLM."""
        system = (
            "You are a helpful personal assistant with excellent memory. "
            "Use any provided context (from memory) to give personalised, accurate responses."
        )

        # Build context from memory tiers
        context_parts: List[str] = []
        if state["memory_summary"]:
            context_parts.append(f"Conversation summary so far:\n{state['memory_summary']}")
        if state["retrieved_context"]:
            context_parts.append(f"Relevant facts from memory:\n{state['retrieved_context']}")

        messages: List[Dict[str, str]] = []
        if context_parts:
            messages.append({"role": "system", "content": "\n\n".join(context_parts)})

        # Add recent conversation history (short-term window)
        for msg in state["conversation_history"][-CONTEXT_WINDOW:]:
            messages.append(msg)

        # Add the current user input
        messages.append({"role": "user", "content": state["user_input"]})

        response = self.llm.chat(messages, system=system, model=MODEL_LARGE, max_tokens=400)
        return {
            "response": response,
            "conversation_history": [
                {"role": "user", "content": state["user_input"]},
                {"role": "assistant", "content": response},
            ],
        }

    def _update_memory(self, state: MemoryState) -> dict:
        """Extract and store facts from the latest exchange into long-term memory."""
        exchange = (
            f"User: {state['user_input']}\n"
            f"Assistant: {state['response']}"
        )
        prompt = (
            "Extract factual information about people, dates, preferences, or entities "
            "from this conversation exchange. Return ONLY a JSON object of key-value pairs "
            "(snake_case keys). Return {} if nothing worth remembering.\n\n"
            f"Exchange:\n{exchange}\n\nJSON:"
        )
        raw = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=256)
        match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        new_facts: Dict[str, Any] = {}
        if match:
            try:
                new_facts = json.loads(match.group())
            except json.JSONDecodeError:
                pass

        updated_ltm = {**state["long_term_memory"], **new_facts}
        return {
            "long_term_memory": updated_ltm,
            "turn_count": state["turn_count"] + 1,
        }

    def _summarize_if_needed(self, state: MemoryState) -> dict:
        """If conversation is long, compress old turns into a summary."""
        history = state["conversation_history"]
        if len(history) <= SUMMARY_THRESHOLD * 2:
            return {}

        old_turns = history[: -CONTEXT_WINDOW]
        old_text = "\n".join(
            f"{msg['role'].title()}: {msg['content']}" for msg in old_turns
        )
        prompt = (
            "Compress the following conversation turns into a brief factual summary "
            "(≤100 words) preserving all important information:\n\n"
            f"{old_text}\n\nSummary:"
        )
        summary = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=150)
        existing = state["memory_summary"]
        combined = f"{existing} {summary}".strip() if existing else summary
        return {"memory_summary": combined}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(MemoryState)

        graph.add_node("retrieve_memory", self._retrieve_memory)
        graph.add_node("generate_response", self._generate_response)
        graph.add_node("update_memory", self._update_memory)
        graph.add_node("summarize_if_needed", self._summarize_if_needed)

        graph.add_edge(START, "retrieve_memory")
        graph.add_edge("retrieve_memory", "generate_response")
        graph.add_edge("generate_response", "update_memory")
        graph.add_edge("update_memory", "summarize_if_needed")
        graph.add_edge("summarize_if_needed", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        """
        Simulates a 4-turn conversation demonstrating all three memory tiers.
        input_data is used as the topic/context for the conversation.
        """
        try:
            app = self.build_graph()

            # Simulated 4-turn conversation
            turns = [
                f"Tell me about {input_data}. My name is Alex Chen and I'm a software engineer.",
                "What programming languages should I learn next given my background?",
                "Can you remind me what you know about me so far?",
                "Based on everything we've discussed, what's a good career path for me?",
            ]

            shared_state: MemoryState = {
                "user_input": "",
                "conversation_history": [],
                "long_term_memory": {},
                "retrieved_context": "",
                "response": "",
                "memory_summary": "",
                "turn_count": 0,
            }

            all_responses = []
            total_elapsed = 0.0

            for turn_input in turns:
                shared_state["user_input"] = turn_input
                result, elapsed = self._timed_run(app.invoke, shared_state)
                total_elapsed += elapsed
                # Persist state across turns
                shared_state = {
                    "user_input": "",
                    "conversation_history": result["conversation_history"],
                    "long_term_memory": result["long_term_memory"],
                    "retrieved_context": "",
                    "response": "",
                    "memory_summary": result["memory_summary"],
                    "turn_count": result["turn_count"],
                }
                all_responses.append({
                    "turn": result["turn_count"],
                    "user": turn_input,
                    "assistant": result["response"],
                })

            final_response = all_responses[-1]["assistant"] if all_responses else ""
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final_response,
                elapsed_ms=total_elapsed,
                steps=all_responses,
                metadata={
                    "total_turns": shared_state["turn_count"],
                    "long_term_facts_stored": len(shared_state["long_term_memory"]),
                    "long_term_memory": shared_state["long_term_memory"],
                    "has_summary": bool(shared_state["memory_summary"]),
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )

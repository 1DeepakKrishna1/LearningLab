"""
Pattern 15: Inter-Agent Communication (A2A)
=============================================
Concept: Agents communicate through a typed message bus. Each agent can
publish messages to the bus and read messages addressed to it. A router
node dispatches the next agent based on pending messages.

Message types:
  - TASK       : assign work to an agent
  - RESULT     : an agent reports its output
  - QUERY      : an agent requests information from another
  - RESPONSE   : reply to a QUERY
  - BROADCAST  : informational message to all agents

Agents:
  - Reporter      : investigates a topic, publishes RAW_STORY
  - FactChecker   : validates claims in the story, publishes VERDICT
  - Editor        : integrates story + verdict, publishes FINAL_ARTICLE

Graph:  START → reporter_agent → fact_checker_agent → editor_agent → publish → END
        (Each agent communicates via the shared message_bus in state)

Demo:   "Write a news article about the latest advances in quantum computing"
"""
from __future__ import annotations

import traceback
from typing import Annotated, Any, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

# ------------------------------------------------------------------ Message types

def _make_message(sender: str, recipient: str, msg_type: str, content: str, metadata: Dict = None) -> Dict[str, Any]:
    return {
        "from": sender,
        "to": recipient,
        "type": msg_type,
        "content": content,
        "metadata": metadata or {},
    }


# ------------------------------------------------------------------ State

class A2AState(TypedDict):
    topic: str
    message_bus: Annotated[List[Dict[str, Any]], operator.add]
    reporter_output: str
    factcheck_verdict: str
    editor_draft: str
    published_article: str
    agent_log: Annotated[List[Dict], operator.add]


class PatternInterAgentCommunication(BasePattern):
    PATTERN_NUMBER = 15
    PATTERN_NAME = "Inter-Agent Communication (A2A)"
    DESCRIPTION = (
        "Agents publish/subscribe on a shared typed message bus; a router dispatches work."
    )

    def _get_messages_for(self, state: A2AState, recipient: str) -> List[Dict]:
        return [m for m in state["message_bus"] if m["to"] == recipient or m["to"] == "all"]

    # ------------------------------------------------------------------ nodes

    def _reporter_agent(self, state: A2AState) -> dict:
        # Read any TASK messages for reporter
        tasks = [m for m in state["message_bus"] if m["to"] == "reporter" and m["type"] == "TASK"]
        task_content = tasks[-1]["content"] if tasks else f"Investigate: {state['topic']}"

        prompt = (
            f"You are an investigative journalist. {task_content}\n\n"
            "Write a 200-word news article draft including:\n"
            "1. A compelling headline\n"
            "2. Lead paragraph (who, what, where, when, why)\n"
            "3. Key facts and quotes (use plausible fictional sources)\n"
            "4. Background context"
        )
        article = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system="You are a veteran investigative journalist known for accuracy.",
            model=MODEL_LARGE,
            max_tokens=500,
        )

        outbox = [
            _make_message(
                sender="reporter",
                recipient="fact_checker",
                msg_type="TASK",
                content=f"Please verify the claims in this article draft:\n\n{article}",
                metadata={"article_length": len(article)},
            ),
            _make_message(
                sender="reporter",
                recipient="all",
                msg_type="BROADCAST",
                content="Reporter has completed initial investigation.",
            ),
        ]
        return {
            "reporter_output": article,
            "message_bus": outbox,
            "agent_log": [{"agent": "reporter", "action": "article_drafted", "chars": len(article)}],
        }

    def _fact_checker_agent(self, state: A2AState) -> dict:
        tasks = [m for m in state["message_bus"] if m["to"] == "fact_checker" and m["type"] == "TASK"]
        article = state["reporter_output"]

        prompt = (
            f"You are a rigorous fact-checker. Review the following article for:\n"
            "1. Factual accuracy of claims\n"
            "2. Unsupported assertions\n"
            "3. Misleading framing\n"
            "4. Missing context\n\n"
            f"Article:\n{article}\n\n"
            "Return a structured verdict: VERIFIED claims (bullet list), "
            "NEEDS_CORRECTION items, and OVERALL_RATING (Accurate/Mostly Accurate/Needs Work)."
        )
        verdict = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system="You are a senior fact-checker at a prestigious news organisation.",
            model=MODEL_LARGE,
            max_tokens=400,
        )

        outbox = [
            _make_message(
                sender="fact_checker",
                recipient="editor",
                msg_type="RESULT",
                content=verdict,
                metadata={"type": "fact_check_verdict"},
            ),
            _make_message(
                sender="fact_checker",
                recipient="reporter",
                msg_type="RESPONSE",
                content="Fact-check complete. Verdict sent to editor.",
            ),
        ]
        return {
            "factcheck_verdict": verdict,
            "message_bus": outbox,
            "agent_log": [{"agent": "fact_checker", "action": "verdict_issued", "chars": len(verdict)}],
        }

    def _editor_agent(self, state: A2AState) -> dict:
        fact_check_msgs = [
            m for m in state["message_bus"]
            if m["to"] == "editor" and m["type"] == "RESULT"
        ]
        verdict = fact_check_msgs[-1]["content"] if fact_check_msgs else state["factcheck_verdict"]

        prompt = (
            "You are the chief editor. Combine the reporter's draft and the fact-checker's verdict "
            "to produce a polished, publication-ready article.\n\n"
            f"Reporter's Draft:\n{state['reporter_output']}\n\n"
            f"Fact-Checker's Verdict:\n{verdict}\n\n"
            "Instructions:\n"
            "- Incorporate all verified claims\n"
            "- Fix or remove claims marked NEEDS_CORRECTION\n"
            "- Ensure the article is professional, engaging, and balanced\n"
            "- Keep it ≤250 words"
        )
        final_article = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system="You are an experienced chief editor maintaining the highest journalistic standards.",
            model=MODEL_LARGE,
            max_tokens=600,
        )

        outbox = [
            _make_message(
                sender="editor",
                recipient="all",
                msg_type="BROADCAST",
                content="Article approved for publication.",
                metadata={"status": "ready"},
            ),
        ]
        return {
            "editor_draft": final_article,
            "message_bus": outbox,
            "agent_log": [{"agent": "editor", "action": "article_edited", "chars": len(final_article)}],
        }

    def _publish(self, state: A2AState) -> dict:
        total_messages = len(state["message_bus"])
        message_type_counts: Dict[str, int] = {}
        for m in state["message_bus"]:
            t = m["type"]
            message_type_counts[t] = message_type_counts.get(t, 0) + 1

        return {
            "published_article": state["editor_draft"],
            "agent_log": [{
                "agent": "publisher",
                "action": "published",
                "total_messages_on_bus": total_messages,
                "message_types": message_type_counts,
            }],
        }

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(A2AState)

        graph.add_node("reporter_agent", self._reporter_agent)
        graph.add_node("fact_checker_agent", self._fact_checker_agent)
        graph.add_node("editor_agent", self._editor_agent)
        graph.add_node("publish", self._publish)

        graph.add_edge(START, "reporter_agent")
        graph.add_edge("reporter_agent", "fact_checker_agent")
        graph.add_edge("fact_checker_agent", "editor_agent")
        graph.add_edge("editor_agent", "publish")
        graph.add_edge("publish", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            # Seed the message bus with the initial task for the reporter
            initial_message = _make_message(
                sender="user",
                recipient="reporter",
                msg_type="TASK",
                content=f"Investigate and write an article about: {input_data}",
            )
            initial: A2AState = {
                "topic": input_data,
                "message_bus": [initial_message],
                "reporter_output": "",
                "factcheck_verdict": "",
                "editor_draft": "",
                "published_article": "",
                "agent_log": [],
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["published_article"],
                elapsed_ms=elapsed_ms,
                steps=final["agent_log"],
                metadata={
                    "total_messages": len(final["message_bus"]),
                    "agents_collaborated": ["reporter", "fact_checker", "editor"],
                    "message_types": list({m["type"] for m in final["message_bus"]}),
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )

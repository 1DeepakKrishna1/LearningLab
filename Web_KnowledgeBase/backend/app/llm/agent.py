"""RAG + agentic reasoning + content understanding, built on the OpenAI client."""
from __future__ import annotations

import json
import re
from typing import Iterator, Optional

from ..models import ChatMessage, ReasoningStep, Source
from ..rag.knowledge_base import KnowledgeBase
from ..rag.vectorstore import ChunkRecord
from . import client, prompts

_CITE_RE = re.compile(r"\[(\d{1,3})\]")


def _snippet(text: str, limit: int = 320) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


class SourceCollector:
    """Assigns stable citation numbers to chunks across one request."""

    def __init__(self) -> None:
        self.records: list[ChunkRecord] = []
        self._seen: dict[tuple[str, str], int] = {}
        self._scores: dict[int, float] = {}

    def add(self, rec: ChunkRecord, score: float) -> int:
        key = (rec.page_id, rec.chunk_id)
        if key in self._seen:
            return self._seen[key]
        n = len(self.records) + 1
        self.records.append(rec)
        self._seen[key] = n
        self._scores[n] = score
        return n

    def as_sources(self, only_cited_in: Optional[str] = None) -> list[Source]:
        cited: Optional[set[int]] = None
        if only_cited_in is not None:
            cited = {int(m) for m in _CITE_RE.findall(only_cited_in)}
        out: list[Source] = []
        for i, rec in enumerate(self.records, start=1):
            if cited is not None and cited and i not in cited:
                continue
            out.append(
                Source(
                    n=i,
                    url=rec.url,
                    title=rec.title,
                    snippet=_snippet(rec.text),
                    page_id=rec.page_id,
                    score=round(self._scores.get(i, 0.0), 4),
                )
            )
        return out or [
            Source(
                n=i,
                url=r.url,
                title=r.title,
                snippet=_snippet(r.text),
                page_id=r.page_id,
                score=round(self._scores.get(i, 0.0), 4),
            )
            for i, r in enumerate(self.records, start=1)
        ]


def _history_to_messages(history: list[ChatMessage]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in history[-12:]]


# ---------------------------------------------------------------- single-pass
def prepare_single_pass(
    kb: KnowledgeBase, message: str, history: list[ChatMessage], top_k: int
) -> tuple[list[dict], list[Source]]:
    """Retrieve once, build the prompt, return (messages, sources)."""
    hits = kb.search(message, top_k)
    collector = SourceCollector()
    numbered: list[tuple[int, ChunkRecord]] = []
    for score, rec in hits:
        n = collector.add(rec, score)
        numbered.append((n, rec))

    system = prompts.ANSWER_SYSTEM.format(kb=prompts.kb_descriptor(kb.meta.domain))
    if numbered:
        context = prompts.format_sources(numbered)
        user = f"Sources:\n\n{context}\n\n---\n\nQuestion: {message}"
    else:
        user = (
            f"No sources were found in the portal for this question.\n\nQuestion: {message}\n\n"
            "Tell the user the portal does not appear to cover this."
        )

    messages = [{"role": "system", "content": system}, *_history_to_messages(history), {"role": "user", "content": user}]
    return messages, collector.as_sources()


def stream_answer(messages: list[dict]) -> Iterator[str]:
    yield from client.stream_chat(messages)


# ------------------------------------------------------------------- agentic
def _search_tool_def() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the knowledge portal for passages relevant to a query. "
            "Returns numbered passages you must cite as [n].",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "A focused search query."},
                },
                "required": ["query"],
            },
        },
    }


def agentic_answer(
    kb: KnowledgeBase,
    message: str,
    history: list[ChatMessage],
    top_k: int,
    *,
    max_iterations: int = 5,
) -> tuple[str, list[Source], list[ReasoningStep]]:
    collector = SourceCollector()
    steps: list[ReasoningStep] = []
    system = prompts.AGENT_SYSTEM.format(kb=prompts.kb_descriptor(kb.meta.domain))
    messages = [
        {"role": "system", "content": system},
        *_history_to_messages(history),
        {"role": "user", "content": message},
    ]
    tools = [_search_tool_def()]

    answer = ""
    for _ in range(max_iterations):
        resp = client.chat(messages, tools=tools)
        choice = resp.choices[0].message

        if not choice.tool_calls:
            answer = choice.content or ""
            break

        messages.append(
            {
                "role": "assistant",
                "content": choice.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in choice.tool_calls
                ],
            }
        )

        for tc in choice.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            query = (args.get("query") or "").strip() or message
            steps.append(ReasoningStep(type="search", detail=query))

            hits = kb.search(query, top_k)
            numbered: list[tuple[int, ChunkRecord]] = []
            for score, rec in hits:
                n = collector.add(rec, score)
                numbered.append((n, rec))

            result = prompts.format_sources(numbered) if numbered else "No matching passages found."
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    else:
        # Loop exhausted without a final answer: force one last synthesis.
        messages.append(
            {"role": "user", "content": "Now answer the original question using the retrieved sources, citing them as [n]."}
        )
        answer = client.chat(messages).choices[0].message.content or ""

    steps.append(ReasoningStep(type="answer", detail="Synthesized answer from retrieved sources."))
    return answer, collector.as_sources(only_cited_in=answer), steps


# --------------------------------------------------------- content understanding
_UNDERSTAND_PROMPTS = {
    "summary": (
        "Summarize the following content into a clear, faithful summary of 3-6 sentences. "
        "Do not add information that is not present."
    ),
    "topics": (
        "Extract the main topics covered in the following content. "
        "Return a concise bulleted list of topic labels (no explanations)."
    ),
    "insights": (
        "Generate the key insights and takeaways from the following content as a short bulleted list. "
        "Each bullet should be a specific, useful insight grounded in the text."
    ),
    "classify": (
        "Classify the following content. Return: a one-line content type/category, "
        "an audience, and 3-6 topical tags. Format as labeled lines."
    ),
}


def understand(mode: str, text: str, title: str = "") -> str:
    instruction = _UNDERSTAND_PROMPTS.get(mode, _UNDERSTAND_PROMPTS["summary"])
    body = text[:14000]
    header = f"Title: {title}\n\n" if title else ""
    messages = [
        {"role": "system", "content": "You analyze documents accurately and never invent details."},
        {"role": "user", "content": f"{instruction}\n\n{header}Content:\n{body}"},
    ]
    return client.chat(messages, temperature=0.2).choices[0].message.content or ""

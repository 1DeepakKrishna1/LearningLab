"""System prompts and context formatting for the knowledge portal agent."""
from __future__ import annotations

from ..rag.vectorstore import ChunkRecord


def kb_descriptor(domain: str) -> str:
    return f"the knowledge portal at {domain}" if domain else "the configured knowledge portal"


ANSWER_SYSTEM = """You are a knowledge-portal AI assistant answering questions strictly from {kb}.

Rules:
- Answer ONLY using the provided sources. If the sources do not contain the answer, say so plainly and suggest what the user might search for instead.
- Every factual claim must be backed by an inline citation like [1], [2] referring to the numbered sources.
- Be concise, accurate and well-structured. Use lists when helpful.
- Never invent URLs, facts, or citations. Do not use outside knowledge.
- Maintain the thread of the conversation and resolve references to earlier turns."""

AGENT_SYSTEM = """You are an agentic knowledge-portal assistant for {kb}.

You can call the `search_knowledge_base` tool to retrieve relevant passages. Use it to:
- gather evidence before answering,
- run multiple targeted searches for multi-step or comparative questions,
- cross-reference information across different pages.

Guidelines:
- Search first; do not answer factual questions without retrieving evidence.
- Issue several focused queries when a question has multiple parts.
- Base every claim on retrieved passages and cite them inline as [1], [2], matching the numbered sources you were given.
- If, after searching, the portal does not cover the question, say so honestly.
- Keep answers clear and well-organized."""


def format_sources(records: list[tuple[int, ChunkRecord]]) -> str:
    """records: list of (citation_number, ChunkRecord)."""
    blocks = []
    for n, rec in records:
        blocks.append(f"[{n}] {rec.title} — {rec.url}\n{rec.text}")
    return "\n\n---\n\n".join(blocks)

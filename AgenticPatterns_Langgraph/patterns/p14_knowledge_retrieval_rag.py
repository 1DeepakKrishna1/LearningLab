"""
Pattern 14: Knowledge Retrieval (RAG)
=======================================
Concept: Build an in-memory knowledge base, retrieve relevant chunks using
TF-IDF cosine similarity (pure stdlib — no external embedding APIs), augment
the LLM prompt with the retrieved context, and generate a grounded answer.

RAG pipeline:
  1. Index   — tokenise and build TF-IDF vectors for all documents
  2. Retrieve — score query against all documents using cosine similarity
  3. Rerank  — keep top-k by score, filter below threshold
  4. Augment — inject retrieved chunks into the prompt
  5. Generate — LLM answers using only the provided context

Graph:  START → index_kb → retrieve_chunks → rank_and_filter
              → augment_prompt → generate_answer → END

Demo:   Answer three questions about Python using a built-in 10-chunk corpus.
"""
from __future__ import annotations

import math
import re
import traceback
from collections import Counter
from typing import Annotated, Any, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE

TOP_K = 3
SIMILARITY_THRESHOLD = 0.05

# ------------------------------------------------------------------ Knowledge Base

KNOWLEDGE_BASE: List[Dict[str, str]] = [
    {"id": "py-1", "title": "Python History", "text": (
        "Python was created by Guido van Rossum and first released in 1991. "
        "Van Rossum started the project in the late 1980s at Centrum Wiskunde & Informatica (CWI) "
        "in the Netherlands. He named it after the BBC TV show Monty Python's Flying Circus. "
        "Python 2.0 was released in 2000, and Python 3.0 in 2008."
    )},
    {"id": "py-2", "title": "Python Philosophy", "text": (
        "Python's design philosophy emphasises code readability and simplicity. "
        "The Zen of Python, accessible via 'import this', contains aphorisms like "
        "'Beautiful is better than ugly', 'Explicit is better than implicit', and "
        "'Simple is better than complex'. Python uses indentation to define code blocks."
    )},
    {"id": "py-3", "title": "Python Data Types", "text": (
        "Python has several built-in data types: integers (int), floating-point numbers (float), "
        "complex numbers (complex), strings (str), lists (list), tuples (tuple), "
        "dictionaries (dict), sets (set), frozensets, and booleans (bool). "
        "Python is dynamically typed — variables are bound to objects, not types."
    )},
    {"id": "py-4", "title": "Python Standard Library", "text": (
        "Python's standard library is vast. Key modules include: os (operating system interface), "
        "sys (system-specific parameters), json (JSON encoding/decoding), re (regular expressions), "
        "datetime (dates and times), pathlib (filesystem paths), collections (container datatypes), "
        "itertools (iterator functions), functools (higher-order functions), and unittest (testing)."
    )},
    {"id": "py-5", "title": "Python Performance", "text": (
        "CPython, the reference implementation, is interpreted and generally slower than compiled "
        "languages. Alternatives include PyPy (JIT-compiled, often 10x faster), Cython "
        "(compiles to C), and Numba (JIT for numerical code). For CPU-bound tasks, "
        "NumPy operations are implemented in C and much faster than pure Python loops."
    )},
    {"id": "py-6", "title": "Python Web Frameworks", "text": (
        "Popular Python web frameworks include Django (batteries-included, MVC), "
        "Flask (lightweight microframework), FastAPI (modern async, built on Starlette), "
        "Tornado (async networking), and Bottle (single-file microframework). "
        "FastAPI uses Python type hints to auto-generate OpenAPI documentation."
    )},
    {"id": "py-7", "title": "Python Package Management", "text": (
        "pip is the standard package installer for Python, using PyPI (Python Package Index) "
        "as the default repository. Virtual environments (venv, virtualenv) isolate project "
        "dependencies. Modern tools include Poetry (dependency management + packaging), "
        "PDM, and uv (extremely fast Rust-based installer)."
    )},
    {"id": "py-8", "title": "Python Async Programming", "text": (
        "Python 3.4 introduced asyncio for asynchronous I/O using coroutines. "
        "The async/await syntax (Python 3.5+) makes async code readable. "
        "Key concepts: event loop, coroutines (defined with async def), "
        "tasks (scheduled coroutines), and awaitables. Popular async frameworks: "
        "asyncio, aiohttp, Trio, and anyio."
    )},
    {"id": "py-9", "title": "Python Type Hints", "text": (
        "Python 3.5 introduced optional type hints via PEP 484. "
        "The typing module provides generics like List[int], Dict[str, Any], Optional[str]. "
        "Python 3.10+ supports X | Y union syntax. Static type checkers include mypy, "
        "pyright, and pytype. Type hints improve IDE support and documentation without "
        "affecting runtime behaviour."
    )},
    {"id": "py-10", "title": "Python Use Cases", "text": (
        "Python is widely used for: web development (Django, FastAPI), data science "
        "(pandas, NumPy, Jupyter), machine learning (scikit-learn, PyTorch, TensorFlow), "
        "automation/scripting, DevOps (Ansible, Fabric), scientific computing (SciPy), "
        "NLP (NLTK, spaCy, Hugging Face Transformers), and system administration. "
        "It is consistently ranked among the top 3 most popular programming languages."
    )},
]


# ------------------------------------------------------------------ TF-IDF helpers (stdlib only)

def _tokenise(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z]{2,}", text.lower())


def _tf(tokens: List[str]) -> Dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {word: count / total for word, count in counts.items()}


def _idf(corpus_tokens: List[List[str]]) -> Dict[str, float]:
    n = len(corpus_tokens)
    df: Dict[str, int] = {}
    for doc_tokens in corpus_tokens:
        for word in set(doc_tokens):
            df[word] = df.get(word, 0) + 1
    return {word: math.log((n + 1) / (count + 1)) + 1.0 for word, count in df.items()}


def _tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf_scores = _tf(tokens)
    return {word: tf_val * idf.get(word, 1.0) for word, tf_val in tf_scores.items()}


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    dot = sum(vec_a.get(w, 0.0) * vec_b.get(w, 0.0) for w in vec_b)
    norm_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    norm_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ------------------------------------------------------------------ State & Pattern

class RAGState(TypedDict):
    query: str
    indexed_docs: List[Dict[str, Any]]   # [{id, title, text, tokens, tfidf}]
    idf_table: Dict[str, float]
    retrieved_chunks: List[Dict[str, Any]]
    retrieval_scores: List[float]
    augmented_prompt: str
    answer: str
    sources_used: List[str]


class PatternKnowledgeRetrievalRAG(BasePattern):
    PATTERN_NUMBER = 14
    PATTERN_NAME = "Knowledge Retrieval (RAG)"
    DESCRIPTION = (
        "TF-IDF retrieval over an in-memory KB, augmented LLM generation."
    )

    # ------------------------------------------------------------------ nodes

    def _index_kb(self, state: RAGState) -> dict:
        """Tokenise all documents and compute IDF table."""
        all_tokens: List[List[str]] = []
        indexed: List[Dict[str, Any]] = []
        for doc in KNOWLEDGE_BASE:
            tokens = _tokenise(doc["title"] + " " + doc["text"])
            all_tokens.append(tokens)
            indexed.append({**doc, "tokens": tokens})

        idf = _idf(all_tokens)
        # Attach TF-IDF vectors
        for i, doc in enumerate(indexed):
            doc["tfidf"] = _tfidf_vector(doc["tokens"], idf)

        return {"indexed_docs": indexed, "idf_table": idf}

    def _retrieve_chunks(self, state: RAGState) -> dict:
        """Score the query against all documents."""
        query_tokens = _tokenise(state["query"])
        query_vec = _tfidf_vector(query_tokens, state["idf_table"])

        scored = []
        for doc in state["indexed_docs"]:
            sim = _cosine_similarity(query_vec, doc["tfidf"])
            scored.append((sim, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:TOP_K]
        chunks = [doc for _, doc in top]
        scores = [round(sim, 4) for sim, _ in top]
        return {"retrieved_chunks": chunks, "retrieval_scores": scores}

    def _rank_and_filter(self, state: RAGState) -> dict:
        """Filter chunks below the similarity threshold."""
        filtered = [
            (chunk, score)
            for chunk, score in zip(state["retrieved_chunks"], state["retrieval_scores"])
            if score >= SIMILARITY_THRESHOLD
        ]
        if not filtered:
            # Fallback: keep top-1 regardless of threshold
            filtered = [(state["retrieved_chunks"][0], state["retrieval_scores"][0])] if state["retrieved_chunks"] else []
        chunks = [c for c, _ in filtered]
        scores = [s for _, s in filtered]
        return {
            "retrieved_chunks": chunks,
            "retrieval_scores": scores,
            "sources_used": [c["id"] for c in chunks],
        }

    def _augment_prompt(self, state: RAGState) -> dict:
        context_parts = []
        for chunk, score in zip(state["retrieved_chunks"], state["retrieval_scores"]):
            context_parts.append(
                f"[Source: {chunk['id']} — {chunk['title']} | relevance: {score}]\n{chunk['text']}"
            )
        context = "\n\n".join(context_parts)
        prompt = (
            f"Answer the following question using ONLY the provided context. "
            f"If the answer is not in the context, say 'I don't have that information'.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {state['query']}\n\nAnswer:"
        )
        return {"augmented_prompt": prompt}

    def _generate_answer(self, state: RAGState) -> dict:
        answer = self.llm.simple_prompt(state["augmented_prompt"], model=MODEL_LARGE, max_tokens=400)
        return {"answer": answer}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(RAGState)

        graph.add_node("index_kb", self._index_kb)
        graph.add_node("retrieve_chunks", self._retrieve_chunks)
        graph.add_node("rank_and_filter", self._rank_and_filter)
        graph.add_node("augment_prompt", self._augment_prompt)
        graph.add_node("generate_answer", self._generate_answer)

        graph.add_edge(START, "index_kb")
        graph.add_edge("index_kb", "retrieve_chunks")
        graph.add_edge("retrieve_chunks", "rank_and_filter")
        graph.add_edge("rank_and_filter", "augment_prompt")
        graph.add_edge("augment_prompt", "generate_answer")
        graph.add_edge("generate_answer", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        """
        input_data: a question about Python, or a list of questions.
        """
        try:
            app = self.build_graph()
            questions = input_data if isinstance(input_data, list) else [input_data]
            all_qa: List[Dict[str, Any]] = []
            total_elapsed = 0.0

            for q in questions:
                initial: RAGState = {
                    "query": q,
                    "indexed_docs": [],
                    "idf_table": {},
                    "retrieved_chunks": [],
                    "retrieval_scores": [],
                    "augmented_prompt": "",
                    "answer": "",
                    "sources_used": [],
                }
                final, elapsed = self._timed_run(app.invoke, initial)
                total_elapsed += elapsed
                all_qa.append({
                    "question": q,
                    "answer": final["answer"],
                    "sources": final["sources_used"],
                    "top_score": final["retrieval_scores"][0] if final["retrieval_scores"] else 0,
                })

            output = all_qa[0]["answer"] if len(all_qa) == 1 else all_qa
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=output,
                elapsed_ms=total_elapsed,
                steps=all_qa,
                metadata={
                    "kb_size": len(KNOWLEDGE_BASE),
                    "retrieval_method": "tfidf_cosine",
                    "top_k": TOP_K,
                    "threshold": SIMILARITY_THRESHOLD,
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )

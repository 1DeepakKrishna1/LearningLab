"""
Pattern 14 – Knowledge Retrieval (RAG)
========================================
Retrieval-Augmented Generation (RAG) grounds LLM responses in a
corpus of authoritative documents, reducing hallucinations and
allowing the model to answer questions beyond its training data.

RAG pipeline in this demo:
  1. Ingest:    load and chunk documents into the knowledge base
  2. Retrieve:  score chunks against the query using BM25 (pure Python)
  3. Augment:   inject top-K retrieved chunks as context
  4. Generate:  LLM answers using only the provided context
  5. Attribute: cite source documents in the response

Components:
  • Document       – a text document with metadata
  • Chunk          – a fixed-size segment of a Document
  • BM25Retriever  – pure-Python BM25 retrieval (no external deps)
  • RAGPipeline    – orchestrates ingest → retrieve → generate
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from llm_client import GroqClient
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Document store
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """A source document in the knowledge base."""

    doc_id: str
    title: str
    content: str
    source: str = "internal"

    @property
    def metadata(self) -> dict[str, str]:
        return {"doc_id": self.doc_id, "title": self.title, "source": self.source}


@dataclass
class Chunk:
    """A fixed-size text segment derived from a Document."""

    chunk_id: str
    doc_id: str
    doc_title: str
    text: str
    char_offset: int = 0

    def citation(self) -> str:
        return f"[{self.doc_title}]"


# ---------------------------------------------------------------------------
# BM25 retriever  (pure Python, no external libraries)
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would could should may might shall can to of in on at for "
    "with by from as into through during before after above below "
    "between that this these those it its itself and or but not if".split()
)


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, remove stop words."""
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


class BM25Retriever:
    """
    BM25 (Best Match 25) retrieval over a corpus of Chunks.

    BM25 is a bag-of-words ranking function widely used in IR systems.
    It rewards term frequency in a document while penalising very long
    documents, giving more robust results than simple TF-IDF cosine.

    Tuning parameters (Okapi BM25 defaults):
        k1 = 1.5  — term frequency saturation
        b  = 0.75 — document length normalisation
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._chunks: list[Chunk] = []
        self._tokenized: list[list[str]] = []
        self._df: Counter[str] = Counter()   # document frequency
        self._avgdl: float = 0.0
        self._N: int = 0

    def index(self, chunks: list[Chunk]) -> None:
        """Build the BM25 index from a list of chunks."""
        self._chunks = chunks
        self._tokenized = [_tokenize(c.text) for c in chunks]
        self._N = len(chunks)

        self._df = Counter()
        total_len = 0
        for tokens in self._tokenized:
            total_len += len(tokens)
            for t in set(tokens):
                self._df[t] += 1

        self._avgdl = total_len / max(self._N, 1)
        logger.debug("BM25 index built: %d chunks, avgdl=%.1f", self._N, self._avgdl)

    def retrieve(self, query: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        """
        Return the top-K chunks most relevant to ``query``.

        Returns:
            List of (Chunk, score) sorted by descending BM25 score.
        """
        if not self._chunks:
            return []

        query_tokens = _tokenize(query)
        scores: list[float] = []

        for i, doc_tokens in enumerate(self._tokenized):
            doc_len = len(doc_tokens)
            tf = Counter(doc_tokens)
            score = 0.0
            for qt in query_tokens:
                if qt not in self._df:
                    continue
                idf = math.log(
                    (self._N - self._df[qt] + 0.5) / (self._df[qt] + 0.5) + 1.0
                )
                tf_qt = tf[qt]
                norm_tf = (tf_qt * (self.k1 + 1)) / (
                    tf_qt + self.k1 * (1 - self.b + self.b * doc_len / self._avgdl)
                )
                score += idf * norm_tf
            scores.append(score)

        ranked = sorted(
            ((self._chunks[i], scores[i]) for i in range(self._N) if scores[i] > 0),
            key=lambda x: x[1],
            reverse=True,
        )
        return ranked[:top_k]


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------


def chunk_document(doc: Document, chunk_size: int = 400, overlap: int = 80) -> list[Chunk]:
    """
    Split a document into overlapping fixed-size character chunks.

    Args:
        doc:        Source document.
        chunk_size: Target chunk size in characters.
        overlap:    Overlap between consecutive chunks.
    """
    text = doc.content
    chunks: list[Chunk] = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        # Extend to next sentence boundary if possible
        if end < len(text):
            next_period = text.find(". ", end)
            if next_period != -1 and next_period < end + 100:
                end = next_period + 1

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}_chunk_{idx}",
                    doc_id=doc.doc_id,
                    doc_title=doc.title,
                    text=chunk_text,
                    char_offset=start,
                )
            )
            idx += 1
        start = max(start + chunk_size - overlap, end)

    return chunks


# ---------------------------------------------------------------------------
# RAG pipeline
# ---------------------------------------------------------------------------


@dataclass
class RetrievalResult:
    query: str
    retrieved_chunks: list[tuple[Chunk, float]]
    context: str
    answer: str
    sources: list[str]


_RAG_SYSTEM = """\
You are a helpful assistant that answers questions using ONLY the provided
context documents.  If the answer is not in the context, say so clearly —
do not hallucinate.  Always cite the source document(s) in your answer
using [Document Title] notation.
"""


class RAGPipeline:
    """Ingest → Retrieve → Augment → Generate pipeline."""

    def __init__(self, client: GroqClient, top_k: int = 3) -> None:
        self.client = client
        self.top_k = top_k
        self.retriever = BM25Retriever()
        self._all_chunks: list[Chunk] = []
        self._documents: list[Document] = []

    def ingest(self, documents: list[Document]) -> None:
        """Chunk all documents and build the retrieval index."""
        self._documents = documents
        all_chunks: list[Chunk] = []
        for doc in documents:
            chunks = chunk_document(doc)
            all_chunks.extend(chunks)
            logger.debug("Ingested '%s' → %d chunks", doc.title, len(chunks))
        self._all_chunks = all_chunks
        self.retriever.index(all_chunks)
        logger.info("RAG index ready: %d total chunks from %d documents", len(all_chunks), len(documents))

    async def query(self, question: str) -> RetrievalResult:
        """Execute the full RAG pipeline for a single question."""
        # ── Retrieve ─────────────────────────────────────────────────
        ranked = self.retriever.retrieve(question, top_k=self.top_k)

        if not ranked:
            context = "No relevant documents found."
            sources = []
        else:
            context_parts = []
            sources: list[str] = []
            for chunk, score in ranked:
                context_parts.append(
                    f"[Source: {chunk.doc_title}  (relevance: {score:.2f})]\n{chunk.text}"
                )
                if chunk.doc_title not in sources:
                    sources.append(chunk.doc_title)
            context = "\n\n---\n\n".join(context_parts)

        # ── Augment & Generate ────────────────────────────────────────
        augmented_prompt = (
            f"Context documents:\n\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer (cite sources):"
        )
        answer = await self.client.complete_text(
            augmented_prompt,
            system=_RAG_SYSTEM,
            max_tokens=500,
        )

        return RetrievalResult(
            query=question,
            retrieved_chunks=ranked,
            context=context,
            answer=answer,
            sources=sources,
        )


# ---------------------------------------------------------------------------
# Demo knowledge base
# ---------------------------------------------------------------------------


_DEMO_DOCUMENTS = [
    Document(
        doc_id="doc_tls",
        title="TLS/SSL Security Guide",
        source="internal-security-wiki",
        content="""\
Transport Layer Security (TLS) is a cryptographic protocol that provides end-to-end
security of data sent between applications over the Internet. TLS 1.3, the latest
version, was finalised in RFC 8446 (2018) and offers significant improvements over
TLS 1.2, including reduced handshake latency and removal of legacy cipher suites.

Key improvements in TLS 1.3:
- 0-RTT (Zero Round Trip Time) resumption reduces latency for returning clients.
- Forward secrecy is mandatory: all key exchanges use ephemeral Diffie-Hellman.
- Deprecated algorithms removed: RSA key exchange, SHA-1, RC4, DES, 3DES, MD5.
- The handshake is encrypted earlier, leaking less metadata.

Certificate management best practices:
- Use certificates from trusted Certificate Authorities (CAs).
- Automate renewal with ACME protocol clients such as Certbot (Let's Encrypt).
- Implement HSTS (HTTP Strict Transport Security) with a long max-age.
- Pin certificates for high-security applications using Certificate Transparency logs.
- Monitor certificate expiry with automated alerting (typically 30-day warning).

Common TLS misconfigurations to avoid:
- Allowing TLS 1.0 or 1.1 (vulnerable to POODLE, BEAST attacks).
- Using weak cipher suites (RC4, export-grade ciphers).
- Failing to validate hostname in certificate common name or SANs.
- Not implementing OCSP stapling, causing slow certificate revocation checks.
""",
    ),
    Document(
        doc_id="doc_auth",
        title="API Authentication Patterns",
        source="internal-security-wiki",
        content="""\
REST API authentication ensures that only authorised clients can access protected
resources. The most common authentication mechanisms are:

1. API Keys
   Simple bearer tokens included in the Authorization header or query parameter.
   Easy to implement but offer no built-in expiry or scope management.
   Best practice: rotate keys regularly; store them in secrets managers.

2. OAuth 2.0 / OIDC
   Industry standard for delegated authorization. Clients obtain short-lived
   access tokens (typically JWTs) from an Authorization Server.
   Flows: Authorization Code (web apps), Client Credentials (M2M), Device Flow (IoT).
   PKCE (Proof Key for Code Exchange) must be used for public clients.

3. JWT (JSON Web Tokens)
   Compact, self-contained tokens signed with HMAC-SHA256 or RSA/ECDSA.
   Payload contains claims (sub, iss, exp, aud). Verify signature and expiry on every request.
   Do NOT store sensitive data in JWT payload (it is base64-encoded, not encrypted).

4. mTLS (Mutual TLS)
   Both client and server present certificates. Provides strong identity
   verification for service-to-service communication. Required in zero-trust architectures.

Security considerations:
- Always use HTTPS; never transmit credentials over plain HTTP.
- Implement rate limiting on authentication endpoints to prevent brute force.
- Use constant-time comparison for token validation to prevent timing attacks.
- Log all authentication failures with IP address for anomaly detection.
""",
    ),
    Document(
        doc_id="doc_sqli",
        title="SQL Injection Prevention",
        source="internal-security-wiki",
        content="""\
SQL injection (SQLi) remains one of the most dangerous and prevalent web
vulnerabilities (OWASP Top 10 A03:2021). It occurs when user-supplied input is
concatenated directly into SQL queries, allowing attackers to manipulate database logic.

Attack types:
- Classic / In-band: results returned directly in the HTTP response.
- Blind: no direct output; attacker infers data through boolean or time-based side channels.
- Out-of-band: data exfiltrated via DNS or HTTP callbacks.

Prevention techniques:
1. Parameterised queries / prepared statements (PRIMARY defence)
   Never concatenate user input. Use placeholders:
     cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

2. ORM usage
   Modern ORMs (SQLAlchemy, Django ORM, Hibernate) use parameterised queries by default.
   Avoid raw query methods (Session.execute with string interpolation).

3. Input validation
   Allowlist expected formats (integers, UUIDs, enums). Reject unexpected characters.
   This is a secondary defence only — never rely on it alone.

4. Principle of least privilege
   DB users for applications should have only SELECT/INSERT/UPDATE on required tables.
   Never connect applications with DBA or root credentials.

5. Web Application Firewall (WAF)
   Can detect and block common SQLi patterns but is not a substitute for parameterised queries.

Testing: use sqlmap for automated SQLi scanning in authorised penetration testing engagements.
""",
    ),
]


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class KnowledgeRetrievalPattern(BasePattern):
    """
    Demonstrates Retrieval-Augmented Generation (RAG).

    Documents are ingested, chunked, and indexed.  Incoming questions
    are answered using BM25-retrieved context, with source citations.
    """

    name = "14 · Knowledge Retrieval (RAG)"

    async def run(  # type: ignore[override]
        self,
        questions: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        self.print_header()

        if questions is None:
            questions = [
                "What are the main improvements in TLS 1.3 over TLS 1.2?",
                "How should I implement authentication for a machine-to-machine API?",
                "What is the primary defence against SQL injection attacks?",
                "How do I prevent certificate expiry incidents?",
            ]

        # ── Ingest ────────────────────────────────────────────────────
        pipeline = RAGPipeline(self.client, top_k=2)
        pipeline.ingest(_DEMO_DOCUMENTS)
        self.print_step(
            "Knowledge Base",
            f"Documents: {len(_DEMO_DOCUMENTS)}  |  "
            f"Chunks: {len(pipeline._all_chunks)}  |  "
            f"Retrieval: BM25\n\n"
            + "\n".join(f"  • [{d.doc_id}] {d.title}" for d in _DEMO_DOCUMENTS),
        )

        # ── Retrieve & Generate for each question ─────────────────────
        all_results: list[RetrievalResult] = []
        for i, question in enumerate(questions, start=1):
            self.print_step(f"Query {i}", question)
            result = await pipeline.query(question)

            retrieval_summary = "\n".join(
                f"  [{j+1}] {chunk.doc_title}  (score={score:.2f})"
                for j, (chunk, score) in enumerate(result.retrieved_chunks)
            )
            self.print_step(f"Query {i} › Retrieved Chunks", retrieval_summary)
            self.print_step(f"Query {i} › Generated Answer", result.answer)
            all_results.append(result)

        self.print_result(
            f"Answered {len(questions)} question(s) using {len(_DEMO_DOCUMENTS)} source documents."
        )

        return {
            "documents_indexed": len(_DEMO_DOCUMENTS),
            "chunks_indexed": len(pipeline._all_chunks),
            "queries": [
                {
                    "question": r.query,
                    "sources_used": r.sources,
                    "answer_preview": r.answer[:150] + "…",
                }
                for r in all_results
            ],
        }

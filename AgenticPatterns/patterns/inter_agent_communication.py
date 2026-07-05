"""
Pattern 15 – Inter-Agent Communication (A2A)
=============================================
Agent-to-Agent (A2A) communication enables distributed, loosely-coupled
multi-agent systems where agents collaborate via a structured message
protocol rather than direct function calls.

This implementation models Google's A2A protocol concepts:
  • Agent Card   – describes an agent's identity and capabilities
  • A2AMessage   – typed, routable message envelope
  • AgentMailbox – per-agent async message queue
  • AgentRegistry – central discovery service for agents
  • A2AAgent     – base class for communicating agents

Message types demonstrated:
  REQUEST   – ask another agent to perform a task
  RESPONSE  – reply to a REQUEST
  BROADCAST – send to all agents in the registry
  HANDOFF   – delegate a task to a more capable specialist

Demo workflow (content pipeline):
  Orchestrator  → REQUEST  → ResearchAgent (gather facts)
  ResearchAgent → RESPONSE → Orchestrator
  Orchestrator  → REQUEST  → WriterAgent  (draft article)
  WriterAgent   → REQUEST  → EditorAgent  (review draft)
  EditorAgent   → RESPONSE → WriterAgent  (edits)
  WriterAgent   → RESPONSE → Orchestrator (final article)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from llm_client import GroqClient
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# A2A Protocol types
# ---------------------------------------------------------------------------


class MessageType(str, Enum):
    REQUEST   = "request"
    RESPONSE  = "response"
    BROADCAST = "broadcast"
    HANDOFF   = "handoff"
    ACK       = "ack"


class TaskStatus(str, Enum):
    SUBMITTED  = "submitted"
    WORKING    = "working"
    COMPLETED  = "completed"
    FAILED     = "failed"


@dataclass
class AgentCard:
    """Describes an agent's identity and declared capabilities."""

    agent_id: str
    name: str
    description: str
    skills: list[str]
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "skills": self.skills,
            "version": self.version,
        }


@dataclass
class A2AMessage:
    """A typed, routable message envelope."""

    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: str           # agent_id or "broadcast"
    subject: str
    payload: dict[str, Any]
    correlation_id: Optional[str] = None  # links replies to original requests
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @staticmethod
    def create(
        message_type: MessageType,
        sender_id: str,
        recipient_id: str,
        subject: str,
        payload: dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> "A2AMessage":
        return A2AMessage(
            message_id=str(uuid.uuid4())[:8],
            message_type=message_type,
            sender_id=sender_id,
            recipient_id=recipient_id,
            subject=subject,
            payload=payload,
            correlation_id=correlation_id,
        )

    def reply(self, sender_id: str, payload: dict[str, Any]) -> "A2AMessage":
        """Create a RESPONSE message correlated to this request."""
        return A2AMessage.create(
            message_type=MessageType.RESPONSE,
            sender_id=sender_id,
            recipient_id=self.sender_id,
            subject=f"Re: {self.subject}",
            payload=payload,
            correlation_id=self.message_id,
        )

    def __str__(self) -> str:
        return (
            f"[{self.message_type.value.upper()}] {self.sender_id} → {self.recipient_id} "
            f"| {self.subject} (id={self.message_id})"
        )


# ---------------------------------------------------------------------------
# Agent infrastructure
# ---------------------------------------------------------------------------


class AgentMailbox:
    """Per-agent async message queue."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[A2AMessage] = asyncio.Queue()
        self._received: list[A2AMessage] = []

    async def send(self, message: A2AMessage) -> None:
        await self._queue.put(message)

    async def receive(self, timeout: float = 10.0) -> Optional[A2AMessage]:
        try:
            msg = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            self._received.append(msg)
            return msg
        except asyncio.TimeoutError:
            return None

    @property
    def message_log(self) -> list[A2AMessage]:
        return list(self._received)


class AgentRegistry:
    """
    Central discovery service.

    Agents register their AgentCard on startup; senders route
    messages by looking up the recipient's mailbox.
    """

    def __init__(self) -> None:
        self._cards: dict[str, AgentCard] = {}
        self._mailboxes: dict[str, AgentMailbox] = {}
        self._message_log: list[A2AMessage] = []

    def register(self, card: AgentCard) -> AgentMailbox:
        self._cards[card.agent_id] = card
        mailbox = AgentMailbox()
        self._mailboxes[card.agent_id] = mailbox
        logger.debug("Registered agent: %s (%s)", card.name, card.agent_id)
        return mailbox

    def get_card(self, agent_id: str) -> Optional[AgentCard]:
        return self._cards.get(agent_id)

    def list_agents(self) -> list[AgentCard]:
        return list(self._cards.values())

    async def route(self, message: A2AMessage) -> None:
        """Deliver a message to its recipient's mailbox."""
        self._message_log.append(message)
        logger.debug("Routing: %s", message)

        if message.recipient_id == "broadcast":
            for agent_id, mailbox in self._mailboxes.items():
                if agent_id != message.sender_id:
                    await mailbox.send(message)
        else:
            mailbox = self._mailboxes.get(message.recipient_id)
            if mailbox:
                await mailbox.send(message)
            else:
                logger.warning("No mailbox for recipient: %s", message.recipient_id)

    @property
    def message_log(self) -> list[A2AMessage]:
        return list(self._message_log)


# ---------------------------------------------------------------------------
# A2A Agent base class
# ---------------------------------------------------------------------------


class A2AAgent:
    """
    Base class for agents that communicate via the A2A protocol.

    Subclasses implement ``handle_message()`` to process incoming
    messages and produce replies.
    """

    def __init__(
        self,
        card: AgentCard,
        registry: AgentRegistry,
        client: GroqClient,
    ) -> None:
        self.card = card
        self.registry = registry
        self.client = client
        self.mailbox = registry.register(card)
        self._task_log: list[dict[str, str]] = []

    @property
    def agent_id(self) -> str:
        return self.card.agent_id

    async def send(
        self,
        recipient_id: str,
        subject: str,
        payload: dict[str, Any],
        message_type: MessageType = MessageType.REQUEST,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        msg = A2AMessage.create(
            message_type=message_type,
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            subject=subject,
            payload=payload,
            correlation_id=correlation_id,
        )
        await self.registry.route(msg)
        return msg

    async def send_and_wait(
        self,
        recipient_id: str,
        subject: str,
        payload: dict[str, Any],
        timeout: float = 30.0,
    ) -> Optional[A2AMessage]:
        """Send a REQUEST and block until the correlated RESPONSE arrives."""
        request = await self.send(recipient_id, subject, payload)
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            reply = await self.mailbox.receive(timeout=5.0)
            if reply and reply.correlation_id == request.message_id:
                return reply
        logger.warning("%s: timed out waiting for reply to %s", self.agent_id, request.message_id)
        return None

    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """Override to process an incoming message. Return a reply or None."""
        raise NotImplementedError

    def log_task(self, description: str, result: str) -> None:
        self._task_log.append({"description": description, "result": result[:200]})


# ---------------------------------------------------------------------------
# Specialist agents
# ---------------------------------------------------------------------------


class ResearchAgent(A2AAgent):
    """Gathers facts and produces a research brief."""

    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        if message.message_type != MessageType.REQUEST:
            return None
        topic = message.payload.get("topic", "")
        brief = await self.client.complete_text(
            f"Research this topic and produce a concise brief (150 words) with "
            f"key facts, statistics, and current trends: {topic}",
            system="You are a meticulous researcher. Be factual and specific.",
            max_tokens=350,
        )
        self.log_task(f"Research: {topic}", brief)
        return message.reply(
            sender_id=self.agent_id,
            payload={"brief": brief, "topic": topic, "status": TaskStatus.COMPLETED.value},
        )


class WriterAgent(A2AAgent):
    """Drafts articles from research briefs, requesting editorial review."""

    def __init__(self, card: AgentCard, registry: AgentRegistry, client: GroqClient, editor_id: str) -> None:
        super().__init__(card, registry, client)
        self.editor_id = editor_id

    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        if message.message_type != MessageType.REQUEST:
            return None
        brief = message.payload.get("brief", "")
        topic = message.payload.get("topic", "")

        # Draft the article
        draft = await self.client.complete_text(
            f"Write a 250-word technical article based on this brief:\n\n{brief}",
            system="You are a technical writer. Write clearly for a developer audience.",
            max_tokens=500,
        )

        # Request editorial review via A2A
        editor_reply = await self.send_and_wait(
            recipient_id=self.editor_id,
            subject="Please review this draft",
            payload={"draft": draft, "topic": topic},
        )

        if editor_reply:
            edited = editor_reply.payload.get("edited_draft", draft)
            self.log_task(f"Write + edit: {topic}", edited)
            return message.reply(
                sender_id=self.agent_id,
                payload={"article": edited, "topic": topic, "status": TaskStatus.COMPLETED.value},
            )
        # Fallback if editor didn't respond
        return message.reply(
            sender_id=self.agent_id,
            payload={"article": draft, "topic": topic, "status": TaskStatus.COMPLETED.value},
        )


class EditorAgent(A2AAgent):
    """Reviews drafts for clarity, grammar, and correctness."""

    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        if message.message_type != MessageType.REQUEST:
            return None
        draft = message.payload.get("draft", "")
        edited = await self.client.complete_text(
            f"Edit this article for clarity, grammar, and flow. "
            f"Return only the improved version:\n\n{draft}",
            system="You are a copy editor. Improve without changing the meaning.",
            max_tokens=500,
        )
        self.log_task("Edit draft", edited)
        return message.reply(
            sender_id=self.agent_id,
            payload={"edited_draft": edited, "status": TaskStatus.COMPLETED.value},
        )


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


@dataclass
class A2AResult:
    topic: str
    message_log: list[str]
    final_article: str
    agent_cards: list[dict[str, Any]]


class InterAgentCommunicationPattern(BasePattern):
    """
    Demonstrates A2A (Agent-to-Agent) communication.

    Agents collaborate via a structured message protocol with typed
    envelopes, mailboxes, and a central registry — enabling loose
    coupling and independent scalability.
    """

    name = "15 · Inter-Agent Communication (A2A)"

    async def run(self, topic: str = "Zero-trust security architecture for cloud-native applications") -> A2AResult:  # type: ignore[override]
        self.print_header()
        print(f"Topic: {topic}\n")

        registry = AgentRegistry()

        # ── Register agents ────────────────────────────────────────────
        editor = EditorAgent(
            card=AgentCard(
                agent_id="editor-001",
                name="EditorAgent",
                description="Reviews and improves written content.",
                skills=["copy_editing", "grammar", "clarity"],
            ),
            registry=registry,
            client=self.client,
        )
        writer = WriterAgent(
            card=AgentCard(
                agent_id="writer-001",
                name="WriterAgent",
                description="Drafts technical articles from research briefs.",
                skills=["technical_writing", "article_drafting"],
            ),
            registry=registry,
            client=self.client,
            editor_id=editor.agent_id,
        )
        researcher = ResearchAgent(
            card=AgentCard(
                agent_id="researcher-001",
                name="ResearchAgent",
                description="Gathers facts and produces research briefs.",
                skills=["research", "fact_gathering", "summarisation"],
            ),
            registry=registry,
            client=self.client,
        )

        # Show registry
        cards = registry.list_agents()
        self.print_step(
            "Agent Registry",
            "\n".join(
                f"  [{c.agent_id}] {c.name}  — skills: {', '.join(c.skills)}"
                for c in cards
            ),
        )

        # ── Orchestrated pipeline (simulated orchestrator) ─────────────

        # Step 1: Request research
        self.print_step("Step 1 › Orchestrator → ResearchAgent (REQUEST)", f"Topic: {topic}")
        research_req = await registry._mailboxes[researcher.agent_id].send(
            A2AMessage.create(
                MessageType.REQUEST, "orchestrator", researcher.agent_id,
                "Gather research", {"topic": topic}
            )
        ) or None

        # Have ResearchAgent process its inbox
        research_inbox_msg = await researcher.mailbox.receive(timeout=5.0)
        if research_inbox_msg:
            research_reply = await researcher.handle_message(research_inbox_msg)
            if research_reply:
                await registry.route(research_reply)
                self.print_step("Step 1 › ResearchAgent → Orchestrator (RESPONSE)", research_reply.payload["brief"])

        # Step 2: Forward research to WriterAgent
        brief = ""
        # Retrieve reply from orchestrator's perspective (simulated via direct payload)
        for msg in registry.message_log:
            if msg.sender_id == researcher.agent_id and "brief" in msg.payload:
                brief = msg.payload["brief"]
                break

        if brief:
            self.print_step("Step 2 › Orchestrator → WriterAgent (REQUEST)", "Write article from research brief")
            write_msg = A2AMessage.create(
                MessageType.REQUEST, "orchestrator", writer.agent_id,
                "Write article", {"brief": brief, "topic": topic}
            )
            await registry.route(write_msg)

            # EditorAgent listens in background while WriterAgent works
            async def run_editor() -> None:
                msg = await editor.mailbox.receive(timeout=20.0)
                if msg:
                    reply = await editor.handle_message(msg)
                    if reply:
                        await registry.route(reply)
                        self.print_step("Step 3 › EditorAgent → WriterAgent (RESPONSE)", "Edited draft returned")

            editor_task = asyncio.create_task(run_editor())

            write_inbox_msg = await writer.mailbox.receive(timeout=5.0)
            final_article = ""
            if write_inbox_msg:
                write_reply = await writer.handle_message(write_inbox_msg)
                await editor_task
                if write_reply:
                    await registry.route(write_reply)
                    final_article = write_reply.payload.get("article", "")
                    self.print_step("Step 4 › WriterAgent → Orchestrator (RESPONSE)", final_article)

        # ── Message log ────────────────────────────────────────────────
        log_lines = [str(m) for m in registry.message_log]
        self.print_step("A2A Message Log", "\n".join(log_lines))

        result = A2AResult(
            topic=topic,
            message_log=log_lines,
            final_article=final_article,
            agent_cards=[c.to_dict() for c in cards],
        )
        self.print_result(
            f"A2A pipeline complete | Messages exchanged: {len(registry.message_log)} | "
            f"Agents: {len(cards)}"
        )
        return result

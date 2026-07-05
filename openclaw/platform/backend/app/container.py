"""Composition root — builds and wires every collaborator (Dependency Injection).

A single :class:`Container` is created at app startup and stored on the FastAPI
app state. Routers pull their dependencies from it via ``api/deps.py``; nothing
constructs its own collaborators, which keeps wiring in one auditable place.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .agents.runtime import AgentRuntimeManager
from .ai_builder.generator import WorkflowGenerator
from .api.ws import EventHub
from .config import Settings, get_settings
from .domain.agent import Agent
from .domain.approval import Approval
from .domain.audit import AuditEntry
from .domain.execution import Execution
from .domain.tool import ToolManifest
from .domain.user import User
from .domain.workflow import Workflow
from .engine.services import EngineServices
from .logging_setup import get_logger
from .messaging.factory import build_messaging_provider
from .registry.tool_registry import ToolRegistry
from .security.jwt_handler import JwtHandler
from .services.agent_service import AgentService
from .services.approval_service import ApprovalService
from .services.audit_service import AuditService
from .services.auth_service import AuthService
from .services.chatbot_service import ChatbotService
from .services.execution_service import ExecutionService
from .services.monitoring_service import MonitoringService
from .services.tool_service import ToolService
from .services.workflow_service import WorkflowService
from .storage.json_repository import JsonRepository

logger = get_logger("container")


class Container:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.ensure_tool_library_importable()
        data: Path = self.settings.data_dir

        # --- repositories (storage seam) ---
        self.workflow_repo = JsonRepository(data / "workflows.json", Workflow)
        self.execution_repo = JsonRepository(data / "executions.json", Execution)
        self.agent_repo = JsonRepository(data / "agents.json", Agent)
        self.tool_repo = JsonRepository(data / "tool_registry.json", ToolManifest)
        self.user_repo = JsonRepository(data / "users.json", User)
        self.audit_repo = JsonRepository(data / "audit_logs.json", AuditEntry)
        self.approval_repo = JsonRepository(data / "approvals.json", Approval)

        # --- infrastructure ---
        self.event_hub = EventHub()
        self.jwt = JwtHandler(self.settings.jwt_secret, self.settings.jwt_algorithm,
                              self.settings.jwt_expire_minutes)
        self.registry = ToolRegistry(self.settings, self.tool_repo)
        self.agent_runtime = AgentRuntimeManager(self.settings, self.registry)
        self.messaging = build_messaging_provider(self.settings)

        # --- services ---
        self.audit_service = AuditService(self.audit_repo)
        self.auth_service = AuthService(self.user_repo, self.jwt, self.settings)
        self.workflow_service = WorkflowService(self.workflow_repo)
        self.agent_service = AgentService(self.agent_repo)
        self.tool_service = ToolService(self.registry)
        self.generator = WorkflowGenerator(self.settings, self.registry)

        # Engine services (emit → ws hub, audit → audit service).
        self.engine_services = EngineServices(
            registry=self.registry,
            agent_runtime=self.agent_runtime,
            agent_repo=self.agent_repo,
            approval_repo=self.approval_repo,
            messaging=self.messaging,
            emit=self.event_hub.emit,
            audit=self._audit_adapter,
            default_model=self.settings.default_llm_model,
        )
        self.execution_service = ExecutionService(
            self.settings, self.engine_services, self.workflow_repo, self.execution_repo)
        self.approval_service = ApprovalService(self.approval_repo, self.execution_service)
        self.monitoring_service = MonitoringService(
            self.execution_repo, self.registry, self.agent_runtime,
            running_count_fn=lambda: self.execution_service.running_count)
        self.chatbot_service = ChatbotService(
            self.generator, self.workflow_service, self.execution_service,
            self.tool_service, self.agent_service)

    async def _audit_adapter(self, **kwargs: Any) -> None:
        await self.audit_service.log(**kwargs)

    async def startup(self) -> None:
        """Load the registry from disk (discover on first run) and seed the admin."""
        await self.registry.load()
        await self.auth_service.bootstrap_admin()
        logger.info("Container ready: %d tools, %d workflows",
                    len(self.registry.all()), await self.workflow_repo.count())

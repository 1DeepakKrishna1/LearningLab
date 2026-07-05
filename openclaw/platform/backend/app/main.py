"""FastAPI application factory.

Wires the DI container into the app lifespan, mounts routers, CORS, the WebSocket
event stream, and global error handlers. Run with:

    uvicorn app.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.errors import install_error_handlers
from .api.routes import api_router
from .config import get_settings
from .container import Container
from .logging_setup import configure_logging, get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    container = Container(settings)
    await container.startup()
    app.state.container = container
    logger.info("%s v%s started in %s mode", settings.app_name, __version__, settings.env)
    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version=__version__,
        description=(
            "Agentic Workflow Automation Platform powered by OpenClaw. "
            "Visual workflow design, agent runtime, dynamic tool registry, "
            "human-in-the-loop approvals, and WhatsApp integration."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        container: Container = app.state.container
        return {"status": "ok", "version": __version__,
                "tools": len(container.registry.all())}

    @app.websocket("/ws/events")
    async def events(websocket: WebSocket) -> None:
        container: Container = websocket.app.state.container
        await container.event_hub.connect(websocket)
        try:
            while True:
                await websocket.receive_text()  # keepalive; clients may ping
        except WebSocketDisconnect:
            await container.event_hub.disconnect(websocket)

    return app


app = create_app()

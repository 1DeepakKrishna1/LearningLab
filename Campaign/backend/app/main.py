"""FastAPI application factory and entrypoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import rate_limit_dependency

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app")

_stop_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure schema exists (Alembic is authoritative; this is a convenience for dev).
    Base.metadata.create_all(bind=engine)

    scheduler_task = None
    if settings.ENABLE_SCHEDULER:
        from app.execution.scheduler import scheduler_loop

        _stop_event.clear()
        scheduler_task = asyncio.create_task(scheduler_loop(_stop_event))
        logger.info("Background scheduler launched")

    yield

    _stop_event.set()
    if scheduler_task:
        await scheduler_task


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Self-hosted Omnichannel Campaign Management Platform",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(
        api_router,
        prefix=settings.API_V1_PREFIX,
        dependencies=[Depends(rate_limit_dependency)],
    )

    @app.get("/health", tags=["System"])
    def health():
        return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(request: Request, exc: IntegrityError):  # noqa: ANN001
        logger.warning("IntegrityError on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=409, content={"detail": "Resource conflict or constraint violation"})

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):  # noqa: ANN001
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    return app


app = create_app()

import asyncio
import os
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routes import workflows, agents, tools, library, execution, ai_assistant
from routes import data_models as data_models_route, associations as associations_route
from routes import auth, users, groups, projects, metrics, audit, reviews
from routes import observability as observability_route
from routes import triggers as triggers_route
from routes import config as config_route
import org_config
from dummy_data import initialize_db
from data_models_persistence import load_data_models, load_associations
from portal_persistence import load_portal_data
from runs_persistence import load_mock_runs
from observability_middleware import ObservabilityMiddleware
import observability as obs

app = FastAPI(title=f"{org_config.get_org_name()} Workflow Platform API", version="2.0.0", docs_url="/docs")

# Observability must wrap the app BEFORE CORS so it sees the final response.
app.add_middleware(ObservabilityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-Trace-Id"],
    expose_headers=["X-Trace-Id"],
)


@app.on_event("startup")
async def startup_event():
    truthy_values = ("true", "1", "t", "yes")
    IsMock = os.getenv("ISMOCK", "False").lower() in truthy_values
    initialize_db()
    if IsMock:
        print("Data loaded (mock) - API ready at http://localhost:8000")
    else:
        print("Data loaded - API ready at http://localhost:8000")
    print("Swagger docs at http://localhost:8000/docs")
    load_data_models()
    load_associations()
    load_portal_data()
    load_mock_runs()
    obs.log("info", "API startup complete", source="backend", logger="startup")


# ── Existing routes ───────────────────────────────────────
app.include_router(workflows.router,          prefix="/workflows",     tags=["Workflows"])
app.include_router(agents.router,             prefix="/agents",        tags=["Agents"])
app.include_router(tools.router,              prefix="/tools",         tags=["Tools"])
app.include_router(library.router,            prefix="/library",       tags=["Library"])
app.include_router(execution.router,          prefix="/execution",     tags=["Execution"])
app.include_router(ai_assistant.router,       prefix="/ai",            tags=["AI Assistant"])
app.include_router(data_models_route.router,  prefix="/data-models",   tags=["Data Models"])
app.include_router(associations_route.router, prefix="/associations",  tags=["Associations"])

# ── New enterprise routes ─────────────────────────────────
app.include_router(auth.router,               prefix="/auth",          tags=["Auth"])
app.include_router(users.router,              prefix="/users",         tags=["Users"])
app.include_router(groups.router,             prefix="/groups",        tags=["Groups"])
app.include_router(projects.router,           prefix="/projects",      tags=["Projects"])
app.include_router(metrics.router,            prefix="/metrics",       tags=["Metrics"])
app.include_router(audit.router,              prefix="/audit-logs",    tags=["Audit"])
app.include_router(reviews.router,            prefix="/reviews",       tags=["Reviews"])
app.include_router(observability_route.router, prefix="/observability", tags=["Observability"])
app.include_router(triggers_route.router,     prefix="/triggers",      tags=["Triggers"])
app.include_router(config_route.router,        prefix="/config",        tags=["Config"])


# ── Cron scheduler ────────────────────────────────────────
# In-process minute-resolution scheduler that fires cron triggers on Start
# agents. Lives alongside the API process for simplicity; would be lifted to a
# dedicated worker in production.

_scheduler_task: asyncio.Task | None = None


async def _cron_scheduler_loop():
    last_minute = None
    while True:
        try:
            now = datetime.utcnow().replace(second=0, microsecond=0)
            if now != last_minute:
                last_minute = now
                fired = triggers_route.tick_cron_triggers(now)
                if fired:
                    obs.log(
                        "info", f"Cron scheduler fired {len(fired)} workflow run(s)",
                        source="trigger", logger="scheduler",
                        extra={"run_ids": fired},
                    )
        except Exception as e:  # noqa: BLE001 — scheduler must never die
            obs.log(
                "error", f"Cron scheduler tick failed: {e}",
                source="trigger", logger="scheduler",
            )
        # Sleep until the next minute boundary (with a small slack so we don't
        # double-fire if the loop drifts).
        await asyncio.sleep(60 - (datetime.utcnow().second % 60))


@app.on_event("startup")
async def _start_scheduler():
    global _scheduler_task
    if _scheduler_task is None:
        _scheduler_task = asyncio.create_task(_cron_scheduler_loop())
        obs.log("info", "Cron trigger scheduler started", source="trigger", logger="scheduler")


@app.on_event("shutdown")
async def _stop_scheduler():
    global _scheduler_task
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.api.routers import (
    ai,
    applications,
    auth,
    product_admin,
    reports,
    staff,
    system_admin,
    systems,
)

app = FastAPI(
    title="iAlloc Platform API",
    version="1.0.0",
    description="Config-driven application→examination→evaluation→ranking→"
    "allocation→enrollment platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173",
                   "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # Create tables if they do not exist (idempotent). Seeding is via `python -m app.seed`.
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "iAlloc"}


app.include_router(auth.router)
app.include_router(product_admin.router)
app.include_router(system_admin.router)
app.include_router(systems.router)
app.include_router(applications.router)
app.include_router(staff.router)
app.include_router(ai.router)
app.include_router(reports.router)

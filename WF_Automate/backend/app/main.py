from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import workflows, agents, ai

app = FastAPI(title="Workflow Management API")

# CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])

@app.get("/")
def read_root():
    return {"message": "Workflow management backend is running."}

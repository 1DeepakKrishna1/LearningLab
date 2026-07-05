from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any

from engine.loader import DataLoader
from engine.executor import WorkflowExecutor

app = FastAPI(title="Workflow Execution Engine")

# initialize once using file paths relative to this file
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_FILE = BASE_DIR / "dummy_data.json"
WORKFLOW_FILE = BASE_DIR / "myworkflow.json"

loader = DataLoader(DATA_FILE, WORKFLOW_FILE)
executor = WorkflowExecutor(loader)


class ExecuteRequest(BaseModel):
    workflow_name: str
    start_properties: Dict[str, Any]


class ExecuteResponse(BaseModel):
    end_properties: Dict[str, Any]
    state: Dict[str, Any]
    log: Any


@app.post("/execute", response_model=ExecuteResponse)
async def execute_workflow(request: ExecuteRequest):
    try:
        result = executor.execute(request.workflow_name, request.start_properties)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

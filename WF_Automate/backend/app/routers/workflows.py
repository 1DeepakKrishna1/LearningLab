from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter()

# dummy data
_workflows = [
    {
        "id": 1,
        "name": "Sample Workflow",
        "agents": [1, 2],
        "steps": [
            {"agent": 1, "name": "Step 1", "position": {"x": 50, "y": 50}},
            {"agent": 2, "name": "Step 2", "position": {"x": 250, "y": 50}}
        ],
        "edges": [
            {"source": "1-0", "target": "2-1"}
        ]
    }
]

@router.get("/", response_model=List[Dict[str, Any]])
def list_workflows():
    return _workflows

@router.get("/{workflow_id}")
def get_workflow(workflow_id: int):
    for wf in _workflows:
        if wf["id"] == workflow_id:
            return wf
    return {"error": "Not found"}

@router.post("/")
def create_workflow(wf: Dict[str, Any]):
    # simple in-memory creation
    new_id = max((w["id"] for w in _workflows), default=0) + 1
    wf["id"] = new_id
    _workflows.append(wf)
    return wf

@router.put("/{workflow_id}")
def update_workflow(workflow_id: int, wf: Dict[str, Any]):
    for idx, w in enumerate(_workflows):
        if w["id"] == workflow_id:
            wf["id"] = workflow_id
            _workflows[idx] = wf
            return wf
    return {"error": "Not found"}

@router.post("/{workflow_id}/clone")
def clone_workflow(workflow_id: int):
    for w in _workflows:
        if w["id"] == workflow_id:
            new_id = max((x["id"] for x in _workflows), default=0) + 1
            newwf = w.copy()
            newwf["id"] = new_id
            newwf["name"] = w.get("name", "") + " (clone)"
            _workflows.append(newwf)
            return newwf
    return {"error": "Not found"}

@router.post("/{workflow_id}/run")
def run_workflow(workflow_id: int):
    # simulate step-by-step execution returning details for each step
    for wf in _workflows:
        if wf["id"] == workflow_id:
            steps = []
            for idx, step in enumerate(wf.get("steps", [])):
                steps.append({
                    "step": idx,
                    "agent": step.get("agent"),
                    "status": "completed",
                    "message": f"Step {idx+1} ({step.get('name','')}) executed"
                })
            return {"workflow_id": workflow_id, "status": "completed", "steps": steps}
    return {"error": "Workflow not found"}

from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from models import Workflow, WorkflowCreate, WorkflowUpdate
from db import workflows_db, library_workflow_ids
from persistence import save_user_workflows
import uuid

router = APIRouter()


@router.get("", response_model=List[Workflow])
async def list_workflows():
    # Return only user-created (non-template) workflows
    return [w for w in workflows_db.values() if not w.is_template]


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflows_db[workflow_id]


@router.post("", response_model=Workflow)
async def create_workflow(body: WorkflowCreate):
    wf = Workflow(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        status=body.status,
        nodes=body.nodes,
        edges=body.edges,
        tags=body.tags,
        is_template=False,
    )
    workflows_db[wf.id] = wf
    save_user_workflows()
    return wf


@router.put("/{workflow_id}", response_model=Workflow)
async def update_workflow(workflow_id: str, body: WorkflowUpdate):
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    existing = workflows_db[workflow_id]
    # Use the validated attribute values (not model_dump) so nested
    # WorkflowNode/WorkflowEdge stay as model instances. model_copy(update=...)
    # does NOT re-validate, so feeding it dicts would persist dicts and break
    # execution (n.data access). Re-validate to be safe.
    update_data = {field: getattr(body, field) for field in body.model_fields_set}
    update_data["updated_at"] = datetime.utcnow()
    updated = Workflow.model_validate(
        {**existing.model_dump(), **update_data}
    )
    workflows_db[workflow_id] = updated
    save_user_workflows()
    return updated


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    del workflows_db[workflow_id]
    library_workflow_ids.discard(workflow_id)
    save_user_workflows()
    return {"deleted": workflow_id}

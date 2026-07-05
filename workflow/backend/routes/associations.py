import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from models import WorkflowAssociation, WorkflowAssociationUpsert
from db import workflows_db, workflow_associations_db
from data_models_persistence import save_associations

router = APIRouter()


def _find_by_workflow(workflow_id: str) -> Optional[WorkflowAssociation]:
    """Return the association for the given workflow_id, or None."""
    for assoc in workflow_associations_db.values():
        if assoc.workflow_id == workflow_id:
            return assoc
    return None


@router.get("/workflow/{workflow_id}")
async def get_workflow_association(workflow_id: str):
    """Returns the association for a workflow, or null (not 404) if absent."""
    assoc = _find_by_workflow(workflow_id)
    if assoc is None:
        return None
    return assoc


@router.post("", response_model=WorkflowAssociation)
async def upsert_association(body: WorkflowAssociationUpsert):
    """Create or update the association for a workflow."""
    if body.workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    existing = _find_by_workflow(body.workflow_id)
    now = datetime.utcnow()

    if existing:
        updated = existing.model_copy(
            update={
                "data_model_id": body.data_model_id,
                "project": body.project,
                "environment": body.environment,
                "global_context": body.global_context,
                "input_mappings": body.input_mappings,
                "default_values": body.default_values,
                "validation_rules": body.validation_rules,
                "activity_bindings": body.activity_bindings,
                "updated_at": now,
            }
        )
        workflow_associations_db[existing.id] = updated
        save_associations()
        return updated

    assoc = WorkflowAssociation(
        id=str(uuid.uuid4()),
        workflow_id=body.workflow_id,
        data_model_id=body.data_model_id,
        project=body.project,
        environment=body.environment,
        global_context=body.global_context,
        input_mappings=body.input_mappings,
        default_values=body.default_values,
        validation_rules=body.validation_rules,
        activity_bindings=body.activity_bindings,
        created_at=now,
        updated_at=now,
    )
    workflow_associations_db[assoc.id] = assoc
    save_associations()
    return assoc


@router.delete("/workflow/{workflow_id}")
async def delete_workflow_association(workflow_id: str):
    """Delete the association for a workflow."""
    existing = _find_by_workflow(workflow_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Association not found")
    del workflow_associations_db[existing.id]
    save_associations()
    return {"deleted": existing.id}

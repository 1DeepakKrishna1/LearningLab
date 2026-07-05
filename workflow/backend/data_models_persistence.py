"""Persist data models and workflow associations to JSON files."""
import json
from datetime import datetime

from models import (
    DataModel, DataModelEntity, DataModelField, DataModelRelationship,
    WorkflowAssociation, InputMapping, ActivityBinding,
    FieldType, RelationType, Environment,
)
from db import data_models_db, workflow_associations_db
from config import get_data_dir

_MODELS_FILE = get_data_dir() / "data_models.json"
_ASSOC_FILE = get_data_dir() / "workflow_associations.json"


# ── Data Models ───────────────────────────────────────────

def save_data_models() -> None:
    """Write all data models to data_models.json."""
    records = [m.model_dump(mode="json") for m in data_models_db.values()]
    _MODELS_FILE.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")


def load_data_models() -> None:
    """Read data_models.json and populate data_models_db (skips if file absent)."""
    if not _MODELS_FILE.exists():
        return
    try:
        records = json.loads(_MODELS_FILE.read_text(encoding="utf-8"))
        for rd in records:
            entities = [
                DataModelEntity(
                    id=e["id"],
                    name=e["name"],
                    description=e.get("description", ""),
                    fields=[
                        DataModelField(
                            name=f["name"],
                            field_type=FieldType(f.get("field_type", "string")),
                            required=f.get("required", False),
                            description=f.get("description", ""),
                            validation=f.get("validation"),
                            default_value=f.get("default_value"),
                        )
                        for f in e.get("fields", [])
                    ],
                )
                for e in rd.get("entities", [])
            ]
            relationships = [
                DataModelRelationship(
                    id=r["id"],
                    from_entity=r["from_entity"],
                    to_entity=r["to_entity"],
                    relation_type=RelationType(r.get("relation_type", "one_to_many")),
                    label=r.get("label", ""),
                )
                for r in rd.get("relationships", [])
            ]
            dm = DataModel(
                id=rd["id"],
                name=rd["name"],
                description=rd.get("description", ""),
                entities=entities,
                relationships=relationships,
                created_at=datetime.fromisoformat(rd["created_at"]) if "created_at" in rd else datetime.utcnow(),
                updated_at=datetime.fromisoformat(rd["updated_at"]) if "updated_at" in rd else datetime.utcnow(),
            )
            data_models_db[dm.id] = dm
        print(f"Loaded {len(records)} data model(s) from {_MODELS_FILE.name}")
    except Exception as exc:
        print(f"Could not load {_MODELS_FILE.name}: {exc}")


# ── Workflow Associations ─────────────────────────────────

def save_associations() -> None:
    """Write all workflow associations to workflow_associations.json."""
    records = [a.model_dump(mode="json") for a in workflow_associations_db.values()]
    _ASSOC_FILE.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")


def load_associations() -> None:
    """Read workflow_associations.json and populate workflow_associations_db (skips if file absent)."""
    if not _ASSOC_FILE.exists():
        return
    try:
        records = json.loads(_ASSOC_FILE.read_text(encoding="utf-8"))
        for rd in records:
            input_mappings = [
                InputMapping(
                    source=m["source"],
                    target=m["target"],
                    description=m.get("description", ""),
                )
                for m in rd.get("input_mappings", [])
            ]
            activity_bindings = [
                ActivityBinding(
                    node_id=b["node_id"],
                    agent_name=b["agent_name"],
                    input_mappings=b.get("input_mappings", []),
                    output_mappings=b.get("output_mappings", []),
                )
                for b in rd.get("activity_bindings", [])
            ]
            assoc = WorkflowAssociation(
                id=rd["id"],
                workflow_id=rd["workflow_id"],
                data_model_id=rd.get("data_model_id"),
                project=rd.get("project", ""),
                environment=Environment(rd.get("environment", "dev")),
                global_context=rd.get("global_context", {}),
                input_mappings=input_mappings,
                default_values=rd.get("default_values", {}),
                validation_rules=rd.get("validation_rules", []),
                activity_bindings=activity_bindings,
                created_at=datetime.fromisoformat(rd["created_at"]) if "created_at" in rd else datetime.utcnow(),
                updated_at=datetime.fromisoformat(rd["updated_at"]) if "updated_at" in rd else datetime.utcnow(),
            )
            workflow_associations_db[assoc.id] = assoc
        print(f"Loaded {len(records)} workflow association(s) from {_ASSOC_FILE.name}")
    except Exception as exc:
        print(f"Could not load {_ASSOC_FILE.name}: {exc}")

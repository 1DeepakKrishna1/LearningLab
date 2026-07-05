import os
import json
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException
from dotenv import load_dotenv

from models import (
    DataModel, DataModelCreate, DataModelUpdate, DataModelImport,
    DataModelAISuggest, DataModelEntity, DataModelField, FieldType,
)
from db import data_models_db
from data_models_persistence import save_data_models

load_dotenv()
router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ── JSON Schema field-type mapping ────────────────────────

_JSON_TYPE_MAP = {
    "string": FieldType.STRING,
    "number": FieldType.NUMBER,
    "integer": FieldType.NUMBER,
    "boolean": FieldType.BOOLEAN,
    "object": FieldType.OBJECT,
    "array": FieldType.ARRAY,
}


def _schema_to_entity(entity_name: str, schema_def: dict) -> DataModelEntity:
    """Convert a single JSON Schema definition object into a DataModelEntity."""
    properties = schema_def.get("properties", {})
    required_fields = set(schema_def.get("required", []))
    fields = []
    for field_name, field_def in properties.items():
        raw_type = field_def.get("type", "string")
        # type can be a list e.g. ["string", "null"]
        if isinstance(raw_type, list):
            raw_type = next((t for t in raw_type if t != "null"), "string")
        field_type = _JSON_TYPE_MAP.get(raw_type, FieldType.STRING)
        fields.append(
            DataModelField(
                name=field_name,
                field_type=field_type,
                required=field_name in required_fields,
                description=field_def.get("description", ""),
            )
        )
    return DataModelEntity(
        id=str(uuid.uuid4()),
        name=entity_name,
        description=schema_def.get("description", ""),
        fields=fields,
    )


# ── Endpoints ─────────────────────────────────────────────

@router.get("", response_model=List[DataModel])
async def list_data_models():
    return list(data_models_db.values())


@router.get("/{model_id}", response_model=DataModel)
async def get_data_model(model_id: str):
    if model_id not in data_models_db:
        raise HTTPException(status_code=404, detail="Data model not found")
    return data_models_db[model_id]


@router.post("/import", response_model=DataModel)
async def import_data_model(body: DataModelImport):
    """Parse a JSON Schema and create a DataModel from its definitions."""
    schema = body.json_schema
    title = schema.get("title", "Imported Model")

    # Try definitions / $defs / components.schemas in that order
    definitions: dict = (
        schema.get("definitions")
        or schema.get("$defs")
        or schema.get("components", {}).get("schemas", {})
        or {}
    )

    entities: List[DataModelEntity] = []
    if definitions:
        for def_name, def_schema in definitions.items():
            if isinstance(def_schema, dict):
                entities.append(_schema_to_entity(def_name, def_schema))
    elif schema.get("properties"):
        # Root-level schema with properties – treat as single entity
        entities.append(_schema_to_entity(title, schema))

    dm = DataModel(
        id=str(uuid.uuid4()),
        name=title,
        description=schema.get("description", ""),
        entities=entities,
        relationships=[],
    )
    data_models_db[dm.id] = dm
    save_data_models()
    return dm


@router.post("/ai-suggest", response_model=DataModel)
async def ai_suggest_data_model(body: DataModelAISuggest):
    """Use Groq to suggest a data model for the given workflow."""
    prompt = (
        f"Given a workflow named '{body.workflow_name}' with description "
        f"'{body.workflow_description}', suggest a minimal data model as a JSON object "
        f"with this exact structure: "
        f'{{\"name\": \"...\", \"entities\": [{{\"name\": \"...\", \"description\": \"...\", '
        f'\"fields\": [{{\"name\": \"...\", \"field_type\": \"string|number|boolean|date|object|array\", '
        f'\"required\": true|false, \"description\": \"...\"}}]}}]}}. '
        f"Return ONLY valid JSON, no markdown, no explanation."
    )

    suggested_name = f"{body.workflow_name} Model"
    fallback_entity = DataModelEntity(
        id=str(uuid.uuid4()),
        name="Entity",
        description="",
        fields=[],
    )

    if not GROQ_API_KEY:
        dm = DataModel(
            id=str(uuid.uuid4()),
            name=suggested_name,
            description="",
            entities=[fallback_entity],
            relationships=[],
        )
        data_models_db[dm.id] = dm
        save_data_models()
        return dm

    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.3,
        )
        raw = completion.choices[0].message.content.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        parsed = json.loads(raw)
        entities: List[DataModelEntity] = []
        for ent in parsed.get("entities", []):
            fields = [
                DataModelField(
                    name=f.get("name", "field"),
                    field_type=FieldType(f.get("field_type", "string"))
                    if f.get("field_type") in [e.value for e in FieldType]
                    else FieldType.STRING,
                    required=bool(f.get("required", False)),
                    description=f.get("description", ""),
                )
                for f in ent.get("fields", [])
            ]
            entities.append(
                DataModelEntity(
                    id=str(uuid.uuid4()),
                    name=ent.get("name", "Entity"),
                    description=ent.get("description", ""),
                    fields=fields,
                )
            )

        dm = DataModel(
            id=str(uuid.uuid4()),
            name=parsed.get("name", suggested_name),
            description=parsed.get("description", ""),
            entities=entities if entities else [fallback_entity],
            relationships=[],
        )
    except Exception:
        dm = DataModel(
            id=str(uuid.uuid4()),
            name=suggested_name,
            description="",
            entities=[fallback_entity],
            relationships=[],
        )

    data_models_db[dm.id] = dm
    save_data_models()
    return dm


@router.post("", response_model=DataModel)
async def create_data_model(body: DataModelCreate):
    dm = DataModel(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
        entities=body.entities,
        relationships=body.relationships,
    )
    data_models_db[dm.id] = dm
    save_data_models()
    return dm


@router.put("/{model_id}", response_model=DataModel)
async def update_data_model(model_id: str, body: DataModelUpdate):
    if model_id not in data_models_db:
        raise HTTPException(status_code=404, detail="Data model not found")
    existing = data_models_db[model_id]
    update_data = body.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    updated = existing.model_copy(update=update_data)
    data_models_db[model_id] = updated
    save_data_models()
    return updated


@router.delete("/{model_id}")
async def delete_data_model(model_id: str):
    if model_id not in data_models_db:
        raise HTTPException(status_code=404, detail="Data model not found")
    del data_models_db[model_id]
    save_data_models()
    return {"deleted": model_id}

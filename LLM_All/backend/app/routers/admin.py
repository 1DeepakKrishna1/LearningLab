from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import (
    load_guardrails,
    load_system_config,
    save_guardrails,
    save_system_config,
    settings,
)
from app.database import get_db
from app.dependencies import require_admin
from app.models import Conversation, Message, User
from app.schemas import (
    AnalyticsOut,
    ApiKeysOut,
    ApiKeysUpdate,
    ConversationDetail,
    ConversationOut,
    GuardrailsOut,
    GuardrailsUpdate,
    InsightsOut,
    MessageOut,
    SummaryOut,
    SystemConfigOut,
    SystemConfigUpdate,
)
from app.services.analytics_service import get_analytics, get_insights, get_summary

router = APIRouter()

# ── API Keys ──────────────────────────────────────────────────────────────────


@router.get("/api-keys", response_model=ApiKeysOut)
def get_api_keys(_: User = Depends(require_admin)) -> ApiKeysOut:
    keys = settings.get_all_api_keys()
    masked = {k: ("*" * 8 + v[-4:] if len(v) > 4 else v) for k, v in keys.items()}
    return ApiKeysOut(**masked)


@router.put("/api-keys")
def update_api_keys(
    body: ApiKeysUpdate, _: User = Depends(require_admin)
) -> dict:
    updates = body.model_dump(exclude_none=True)
    for provider, key in updates.items():
        settings.set_api_key(provider, key)
    return {"message": "API keys updated", "updated": list(updates.keys())}


# ── System Config ─────────────────────────────────────────────────────────────


@router.get("/system-config", response_model=SystemConfigOut)
def get_system_config(_: User = Depends(require_admin)) -> SystemConfigOut:
    return SystemConfigOut(**load_system_config())


@router.put("/system-config", response_model=SystemConfigOut)
def update_system_config(
    body: SystemConfigUpdate, _: User = Depends(require_admin)
) -> SystemConfigOut:
    config = load_system_config()
    config["active_llm"] = body.active_llm
    config["system_prompt"] = body.system_prompt
    if body.models:
        config["models"].update(body.models)
    if body.context_window is not None:
        config["context_window"] = body.context_window
    save_system_config(config)
    return SystemConfigOut(**config)


# ── Guardrails ────────────────────────────────────────────────────────────────


@router.get("/guardrails", response_model=GuardrailsOut)
def get_guardrails(_: User = Depends(require_admin)) -> GuardrailsOut:
    return GuardrailsOut(**load_guardrails())


@router.put("/guardrails", response_model=GuardrailsOut)
def update_guardrails(
    body: GuardrailsUpdate, _: User = Depends(require_admin)
) -> GuardrailsOut:
    data = body.model_dump()
    save_guardrails(data)
    return GuardrailsOut(**data)


# ── Conversations ─────────────────────────────────────────────────────────────


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[ConversationOut]:
    convs: list[Conversation] = (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        ConversationOut(
            id=c.id,
            user_id=c.user_id,
            username=c.user.username,
            title=c.title,
            llm_provider=c.llm_provider,
            message_count=len(c.messages),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ConversationDetail:
    conv: Conversation | None = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return ConversationDetail(
        id=conv.id,
        user_id=conv.user_id,
        username=conv.user.username,
        title=conv.title,
        llm_provider=conv.llm_provider,
        message_count=len(conv.messages),
        summary=conv.summary,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[MessageOut.model_validate(m) for m in conv.messages],
    )


@router.get("/conversations/{conversation_id}/analytics", response_model=AnalyticsOut)
def conversation_analytics(
    conversation_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AnalyticsOut:
    try:
        return get_analytics(db, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/conversations/{conversation_id}/summary", response_model=SummaryOut)
def conversation_summary(
    conversation_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> SummaryOut:
    try:
        return get_summary(db, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM unavailable: {exc}")


@router.get("/conversations/{conversation_id}/insights", response_model=InsightsOut)
def conversation_insights(
    conversation_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> InsightsOut:
    try:
        return get_insights(db, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM unavailable: {exc}")

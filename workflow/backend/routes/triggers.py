"""Trigger endpoints for the Start agent.

Each Start agent in a workflow can declare multiple triggers in its
properties.triggers list. Triggers come in five flavours:

  - manual         : default; user clicks Run in the UI
  - webhook        : POST /triggers/webhook/{workflow_id}/{trigger_id}
  - cron           : ticked by the in-process scheduler (main.py)
  - google_sheet   : POST /triggers/google-sheet/{workflow_id}/{trigger_id}
                     (intended to be called by a Google Apps Script onEdit/onChange)
  - email          : POST /triggers/email/{workflow_id}/{trigger_id}
                     (intended to be called by a Power Automate "When new email"
                      flow that forwards the email payload)

All trigger endpoints synchronously kick off `execute_workflow()` and return
the resulting ExecutionRun, so external callers can both fire and inspect the
run in one request.

A `/triggers/simulate` endpoint mirrors the same surface but is intended for
the Studio UI's "Run with…" picker to test trigger handling without hitting
the real external surface.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Body, Request

from models import ExecutionRun, Trigger, TriggerType
from db import workflows_db
from routes.execution import execute_workflow
import observability as obs

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────

def _find_start_node(workflow_id: str):
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")
    wf = workflows_db[workflow_id]
    for node in wf.nodes:
        if node.node_kind == "agent" and node.data.get("type") == "start":
            return wf, node
    raise HTTPException(status_code=400, detail="Workflow has no Start agent")


def _find_trigger(workflow_id: str, trigger_id: str, expected_type: TriggerType):
    wf, start_node = _find_start_node(workflow_id)
    triggers = (start_node.data.get("properties") or {}).get("triggers") or []
    for t in triggers:
        if t.get("id") == trigger_id:
            if t.get("type") != expected_type.value:
                raise HTTPException(
                    status_code=400,
                    detail=f"Trigger {trigger_id} is type '{t.get('type')}', not '{expected_type.value}'",
                )
            if not t.get("enabled", True):
                raise HTTPException(status_code=403, detail="Trigger is disabled")
            return wf, start_node, t
    raise HTTPException(status_code=404, detail="Trigger not found")


def _trigger_context(trigger: Dict[str, Any], payload: Dict[str, Any], simulated: bool = False) -> Dict[str, Any]:
    return {
        "id": trigger.get("id"),
        "type": trigger.get("type"),
        "name": trigger.get("name") or trigger.get("type"),
        "fired_at": datetime.utcnow().isoformat(),
        "simulated": simulated,
        "payload": payload,
    }


def _verify_secret(trigger: Dict[str, Any], request: Request) -> None:
    """If the trigger config has a `secret`, require it on the request.

    Accepted as either ?secret=... query or X-Trigger-Secret header. This is a
    minimal shared-secret check — good enough for first-party Power Automate /
    Google Apps Script callers."""
    expected = (trigger.get("config") or {}).get("secret", "").strip()
    if not expected:
        return
    provided = (
        request.headers.get("x-trigger-secret")
        or request.query_params.get("secret")
        or ""
    ).strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid trigger secret")


# ── Discovery ────────────────────────────────────────────

@router.get("/workflow/{workflow_id}")
async def list_workflow_triggers(workflow_id: str, request: Request):
    """Return all triggers configured on this workflow's Start agent, plus the
    fully-qualified external URLs the UI can show for copy/paste into Power
    Automate, Google Apps Script, etc."""
    wf, start_node = _find_start_node(workflow_id)
    triggers = (start_node.data.get("properties") or {}).get("triggers") or []
    base = str(request.base_url).rstrip("/")

    def _url_for(t: Dict[str, Any]) -> Optional[str]:
        ttype = t.get("type")
        tid = t.get("id")
        if ttype == "webhook":
            return f"{base}/triggers/webhook/{workflow_id}/{tid}"
        if ttype == "google_sheet":
            return f"{base}/triggers/google-sheet/{workflow_id}/{tid}"
        if ttype == "email":
            return f"{base}/triggers/email/{workflow_id}/{tid}"
        return None

    return {
        "workflow_id": workflow_id,
        "workflow_name": wf.name,
        "triggers": [
            {**t, "external_url": _url_for(t)} for t in triggers
        ],
    }


# ── HTTP Webhook ─────────────────────────────────────────

@router.post("/webhook/{workflow_id}/{trigger_id}", response_model=ExecutionRun)
async def fire_webhook(
    workflow_id: str,
    trigger_id: str,
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
):
    wf, start_node, trigger = _find_trigger(workflow_id, trigger_id, TriggerType.WEBHOOK)
    _verify_secret(trigger, request)
    obs.log(
        "info", f"Webhook trigger fired for '{wf.name}'",
        source="trigger", logger="triggers.webhook", workflow_id=workflow_id,
        extra={"trigger_id": trigger_id},
    )
    return execute_workflow(workflow_id, trigger_context=_trigger_context(trigger, payload))


# ── Google Sheet row entry ───────────────────────────────

@router.post("/google-sheet/{workflow_id}/{trigger_id}", response_model=ExecutionRun)
async def fire_google_sheet(
    workflow_id: str,
    trigger_id: str,
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
):
    """Intended caller: a Google Apps Script onChange/onEdit handler that POSTs
    the new row as JSON, e.g. {"row": 42, "values": {"name": "...", ...}}."""
    wf, start_node, trigger = _find_trigger(workflow_id, trigger_id, TriggerType.GOOGLE_SHEET)
    _verify_secret(trigger, request)

    # Optional sheet/range filter from the trigger config — when set, the
    # incoming payload must match for the trigger to fire.
    cfg = trigger.get("config") or {}
    expected_sheet = (cfg.get("sheet_id") or "").strip()
    incoming_sheet = (payload.get("sheet_id") or "").strip()
    if expected_sheet and incoming_sheet and expected_sheet != incoming_sheet:
        raise HTTPException(status_code=400, detail="Sheet id mismatch")

    obs.log(
        "info", f"Google Sheet trigger fired for '{wf.name}'",
        source="trigger", logger="triggers.google_sheet", workflow_id=workflow_id,
        extra={"trigger_id": trigger_id, "sheet_id": incoming_sheet or expected_sheet},
    )
    return execute_workflow(workflow_id, trigger_context=_trigger_context(trigger, payload))


# ── Email receive via Power Automate ─────────────────────

@router.post("/email/{workflow_id}/{trigger_id}", response_model=ExecutionRun)
async def fire_email(
    workflow_id: str,
    trigger_id: str,
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
):
    """Intended caller: a Power Automate flow on 'When a new email arrives'
    that posts {from, subject, body, received_at, attachments?} to this URL."""
    wf, start_node, trigger = _find_trigger(workflow_id, trigger_id, TriggerType.EMAIL)
    _verify_secret(trigger, request)

    # Optional subject/sender filters
    cfg = trigger.get("config") or {}
    subj_filter = (cfg.get("subject_contains") or "").strip().lower()
    from_filter = (cfg.get("from_contains") or "").strip().lower()
    if subj_filter and subj_filter not in str(payload.get("subject", "")).lower():
        return execute_workflow(workflow_id, trigger_context={
            **_trigger_context(trigger, payload),
            "filtered_out": "subject",
        })
    if from_filter and from_filter not in str(payload.get("from", "")).lower():
        return execute_workflow(workflow_id, trigger_context={
            **_trigger_context(trigger, payload),
            "filtered_out": "from",
        })

    obs.log(
        "info", f"Email trigger fired for '{wf.name}' (subject={payload.get('subject', '')[:60]!r})",
        source="trigger", logger="triggers.email", workflow_id=workflow_id,
        extra={"trigger_id": trigger_id},
    )
    return execute_workflow(workflow_id, trigger_context=_trigger_context(trigger, payload))


# ── Manual simulation (from Studio UI) ───────────────────

@router.post("/simulate/{workflow_id}", response_model=ExecutionRun)
async def simulate_trigger(
    workflow_id: str,
    body: Dict[str, Any] = Body(default_factory=dict),
):
    """UI entry point. The Studio "Run with…" picker calls this to test
    trigger handling without hitting the real external surface.

    Body shape: {"trigger_id": "...", "payload": {...}}
        OR     {"trigger_type": "webhook|cron|google_sheet|email|manual",
                "payload": {...}}
    """
    trigger_id = body.get("trigger_id")
    trigger_type = body.get("trigger_type") or "manual"
    payload = body.get("payload") or {}

    # If a saved trigger id was supplied, look it up so we honor its name/config.
    trigger: Dict[str, Any]
    if trigger_id:
        _, _, trigger = _find_trigger(
            workflow_id, trigger_id, TriggerType(trigger_type)
            if trigger_type in TriggerType.__members__.values()
            else TriggerType.MANUAL
        )
    else:
        # Synthetic trigger for ad-hoc "Run with manual" or "Run with cron simulation".
        try:
            ttype = TriggerType(trigger_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown trigger_type '{trigger_type}'")
        trigger = {
            "id": "sim",
            "type": ttype.value,
            "name": f"Simulated {ttype.value}",
            "config": {},
        }

    return execute_workflow(
        workflow_id,
        trigger_context=_trigger_context(trigger, payload, simulated=True),
    )


# ── Cron scheduler hook ──────────────────────────────────

def _matches_cron(expr: str, now: datetime) -> bool:
    """Minimal 5-field cron matcher: 'minute hour day month dow'.

    Each field is one of:  *   |   N   |   */K   |   N,M,...
    Day-of-week is 0-6 with 0 = Monday (Python's weekday()).

    This is not a full RFC-compliant parser; it's enough for the four most
    common cron shapes used in workflow scheduling.
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        return False
    fields = [
        now.minute,
        now.hour,
        now.day,
        now.month,
        now.weekday(),
    ]
    for spec, value in zip(parts, fields):
        if spec == "*":
            continue
        if spec.startswith("*/"):
            try:
                step = int(spec[2:])
            except ValueError:
                return False
            if step <= 0 or value % step != 0:
                return False
            continue
        if "," in spec:
            try:
                allowed = {int(x) for x in spec.split(",")}
            except ValueError:
                return False
            if value not in allowed:
                return False
            continue
        try:
            if int(spec) != value:
                return False
        except ValueError:
            return False
    return True


def tick_cron_triggers(now: Optional[datetime] = None) -> List[str]:
    """Called once per minute from the asyncio scheduler in main.py.

    Walks every workflow's Start agent and fires any cron trigger whose
    expression matches `now`. Returns the list of execution-run ids it kicked
    off (mostly useful for tests / logging).
    """
    now = now or datetime.utcnow()
    fired: List[str] = []
    for wf in workflows_db.values():
        for node in wf.nodes:
            if node.node_kind != "agent" or node.data.get("type") != "start":
                continue
            triggers = (node.data.get("properties") or {}).get("triggers") or []
            for t in triggers:
                if t.get("type") != "cron" or not t.get("enabled", True):
                    continue
                expr = (t.get("config") or {}).get("expression", "").strip()
                if not expr or not _matches_cron(expr, now):
                    continue
                try:
                    run = execute_workflow(
                        wf.id,
                        trigger_context=_trigger_context(t, {"scheduled_for": now.isoformat()}),
                    )
                    fired.append(run.id)
                    t["last_fired_at"] = now.isoformat()
                    obs.log(
                        "info", f"Cron trigger fired '{wf.name}' (expr={expr})",
                        source="trigger", logger="triggers.cron", workflow_id=wf.id,
                        extra={"trigger_id": t.get("id"), "run_id": run.id},
                    )
                except HTTPException as e:
                    obs.log(
                        "warn", f"Cron trigger could not fire '{wf.name}': {e.detail}",
                        source="trigger", logger="triggers.cron", workflow_id=wf.id,
                    )
    return fired

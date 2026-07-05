from fastapi import APIRouter, HTTPException, Body
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict
from types import SimpleNamespace
import random
import re
import json

from models import ExecutionRun, StepResult, ExecutionStatus, AgentType
from db import workflows_db, executions_db, workflow_associations_db, data_models_db
import observability as obs

router = APIRouter()


# ── Agent object from workflow node data ──────────────────
def _agent_from_node(node) -> object:
    """Build an agent-like object from the data stored in the workflow node,
    so execution is self-contained and doesn't depend on agents_db."""
    raw_type = node.data.get("type", "automatic")
    try:
        atype = AgentType(raw_type)
    except ValueError:
        atype = AgentType.AUTOMATIC
    return SimpleNamespace(
        type=atype,
        name=node.data.get("name", "Unknown Agent"),
        properties=node.data.get("properties") or {},
    )


# ── Topological sort (Kahn's algorithm) ───────────────────
def _topo_sort(nodes, edges):
    adj = {n.id: [] for n in nodes}
    in_deg = {n.id: 0 for n in nodes}
    for e in edges:
        if e.source in adj:
            adj[e.source].append(e.target)
        if e.target in in_deg:
            in_deg[e.target] += 1

    queue = [n.id for n in nodes if in_deg[n.id] == 0]
    order = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for nb in adj.get(nid, []):
            in_deg[nb] -= 1
            if in_deg[nb] == 0:
                queue.append(nb)

    node_map = {n.id: n for n in nodes}
    return [node_map[nid] for nid in order if nid in node_map]


# ── Invoke parameter resolution ───────────────────────────

def _create_data_model_instance(data_model) -> dict:
    """Create an empty runtime JSON instance from a DataModel definition."""
    instance = {}
    for entity in data_model.entities:
        entity_data = {}
        for field in entity.fields:
            entity_data[field.name] = field.default_value
        instance[entity.name] = entity_data
    return instance


def _resolve_value(value_type: str, value: str, exec_context: dict) -> Any:
    """Resolve a parameter value from execution context using template references."""
    if value_type == "constant":
        return value

    def _replace_ref(m: re.Match) -> str:
        path = m.group(1).strip().split(".")
        if not path:
            return m.group(0)

        if value_type == "workflow" and path[0] == "wf":
            ctx = exec_context.get("wf", {})
            for part in path[1:]:
                ctx = ctx.get(part, None) if isinstance(ctx, dict) else None
        elif value_type == "tool" and path[0] == "tool":
            ctx = exec_context.get("tool_outputs", {})
            for part in path[1:]:
                ctx = ctx.get(part, None) if isinstance(ctx, dict) else None
        elif value_type == "data_model":
            ctx = exec_context.get("data_model", {})
            for part in path:
                ctx = ctx.get(part, None) if isinstance(ctx, dict) else None
        else:
            return m.group(0)

        return str(ctx) if ctx is not None else ""

    return re.sub(r"\{\{([^}]+)\}\}", _replace_ref, value)


# ── Fake I/O generators ────────────────────────────────────
# Human-in-the-Loop → active collaboration: approve / correct / override / give feedback (model learns).
_HITL_JUDGMENT_OPTIONS   = ["Approve", "Correct Output", "Override Decision", "Provide Feedback"]
# Human Review → validation checkpoint after automation: mostly approve / reject.
_REVIEW_JUDGMENT_OPTIONS = ["Approve", "Reject"]

_AI_RISK_DECISIONS = ["High Risk", "Medium Risk", "Low Risk"]


def _human_step(node, agent, started, duration) -> StepResult:
    """Build a paused step for the frontend popup.

    Distinguishes the two collaboration patterns from the spec:
      • human_in_the_loop → the human is *inside the loop*: can approve, correct the AI
        output, override the decision, or feed back so the model learns. Happens during execution.
      • human_review      → a validation checkpoint *after* the AI produced an artifact:
        the reviewer approves/rejects (verification only, no model learning).
    """
    atype = agent.type if agent else AgentType.HUMAN_IN_THE_LOOP
    agent_props = agent.properties if agent else {}
    agent_name = node.data.get("name") or (agent.name if agent else "Unknown Agent")

    if atype == AgentType.HUMAN_REVIEW:
        # ── Human Review: AI generated an artifact, human validates it ──
        word_count = random.randint(120, 480)
        ai_output = {
            "generated_summary": "AI-drafted contract summary covering parties, term, "
                                 "payment schedule, liability caps, and termination clauses.",
            "word_count": word_count,
            "model": "llama-3.3-70b-versatile",
            "confidence": round(random.uniform(0.82, 0.97), 2),
        }
        input_fields = {
            "edited_summary": ai_output["generated_summary"],
            "reviewer_notes": "",
        }
        # Artifacts the reviewer can download to validate the AI output.
        summary_md = (
            "# Contract Summary (AI Draft)\n\n"
            f"- Model: {ai_output['model']}\n"
            f"- Confidence: {ai_output['confidence']}\n"
            f"- Word count: {word_count}\n\n"
            "## Summary\n"
            f"{ai_output['generated_summary']}\n\n"
            "## Sections Covered\n"
            "- Parties\n- Term\n- Payment schedule\n- Liability caps\n- Termination clauses\n"
        )
        source_txt = (
            "SOURCE CONTRACT (excerpt provided for validation)\n"
            "=================================================\n\n"
            "This Agreement is entered into by and between Party A and Party B as of the "
            "Effective Date. The parties agree to the term, payment schedule, liability "
            "caps, and termination provisions summarised by the automation step.\n\n"
            "[Full source document attached for the reviewer.]\n"
        )
        download_files = [
            {"name": "contract_summary_draft.md", "type": "text/markdown",
             "size_kb": round(len(summary_md) / 1024, 1), "content": summary_md},
            {"name": "source_contract.txt", "type": "text/plain",
             "size_kb": round(len(source_txt) / 1024, 1), "content": source_txt},
        ]

        return StepResult(
            node_id=node.id,
            agent_name=agent_name,
            node_kind="agent",
            status=ExecutionStatus.PENDING,
            started_at=started,
            input={
                "checkpoint": "post-automation validation",
                "assigned_to": agent_props.get("assigned_to", "legal-team@company.com"),
                "stage": "after",
            },
            output={},
            logs=[
                "Automation produced an artifact for validation.",
                "Routing to reviewer at checkpoint…",
                "Awaiting approve / reject decision…",
            ],
            duration_ms=duration,
            requires_human_input=True,
            review_mode="review",
            judgment_options=_REVIEW_JUDGMENT_OPTIONS,
            input_fields=input_fields,
            ai_output=ai_output,
            download_files=download_files,   # reviewer can download artifacts
            allow_upload=False,              # review checkpoint: download only
        )

    # ── Human-in-the-Loop: human collaborates inside the running loop ──
    ai_output = {
        "ai_decision": random.choice(_AI_RISK_DECISIONS),
        "confidence": round(random.uniform(0.55, 0.92), 2),
        "recommended_action": random.choice(["Decline", "Approve", "Escalate"]),
        "rationale": "Model flagged edge-case signals in the application data.",
    }
    input_fields = {
        "corrected_decision": ai_output["ai_decision"],
        "feedback": "",
        "train_model": agent_props.get("train_model", "yes"),
    }
    # Merge any extra simple properties the agent defines
    for k, v in agent_props.items():
        if k not in input_fields and isinstance(v, (str, int, float, bool)):
            input_fields[k] = v

    # Files the human can download to inform their in-loop decision.
    decision_report = (
        "HUMAN-IN-THE-LOOP DECISION REPORT\n"
        "=================================\n\n"
        f"AI Decision: {ai_output['ai_decision']}\n"
        f"Recommended Action: {ai_output['recommended_action']}\n"
        f"Confidence: {ai_output['confidence']}\n"
        f"Rationale: {ai_output['rationale']}\n\n"
        "Review the attached application data and approve, correct, or override the decision.\n"
    )
    application_data = json.dumps({
        "application_id": f"APP-{random.randint(10000, 99999)}",
        "ai_decision": ai_output["ai_decision"],
        "recommended_action": ai_output["recommended_action"],
        "confidence": ai_output["confidence"],
        "signals": ["edge_case_flag", "manual_review_recommended"],
    }, indent=2)
    download_files = [
        {"name": "ai_decision_report.txt", "type": "text/plain",
         "size_kb": round(len(decision_report) / 1024, 1), "content": decision_report},
        {"name": "application_data.json", "type": "application/json",
         "size_kb": round(len(application_data) / 1024, 1), "content": application_data},
    ]

    return StepResult(
        node_id=node.id,
        agent_name=agent_name,
        node_kind="agent",
        status=ExecutionStatus.PENDING,
        started_at=started,
        input={
            "items_pending": random.randint(1, 20),
            "assigned_to": agent_props.get("assigned_to", "analyst@company.com"),
            "stage": "during",
        },
        output={},
        logs=[
            "AI produced a provisional decision.",
            "Pausing loop for human collaboration…",
            "Human may approve, correct, override, or provide feedback…",
        ],
        duration_ms=duration,
        requires_human_input=True,
        review_mode="hitl",
        judgment_options=_HITL_JUDGMENT_OPTIONS,
        input_fields=input_fields,
        ai_output=ai_output,
        download_files=download_files,   # human can download context files
        allow_upload=True,               # in-loop collaboration: allow uploads
    )


def _fake_step(node, agent) -> StepResult:
    atype = agent.type if agent else AgentType.AUTOMATIC
    duration = random.randint(600, 3200)
    started = datetime.utcnow()

    # Human-in-the-loop / human-review: return a paused step for frontend to handle
    if atype in (AgentType.HUMAN_IN_THE_LOOP, AgentType.HUMAN_REVIEW):
        return _human_step(node, agent, started, duration)

    n_iters  = random.randint(2, 5)
    n_tasks  = random.randint(2, 6)
    n_agents = random.randint(2, 5)
    quality  = round(random.uniform(7.5, 9.8), 1)
    tokens   = random.randint(120, 800)

    agent_props = agent.properties if agent else {}

    step_data = {
        AgentType.START: {
            "input": {},
            "output": {
                "config": agent_props,
                "environment": agent_props.get("environment", "production"),
                "version": agent_props.get("version", "1.0.0"),
                "run_label": agent_props.get("run_label", ""),
            },
            "logs": [
                "Workflow Start reached.",
                "Loading workflow configuration…",
                f"Environment: {agent_props.get('environment', 'production')} | Version: {agent_props.get('version', '1.0.0')}",
                "Configuration broadcast to all agents in workflow context.",
                "Workflow execution is now running.",
            ],
        },
        AgentType.END: {
            "input": {"collected_sources": n_agents, "upstream_agents": n_agents},
            "output": {
                "status": "success",
                "total_agents_completed": n_agents,
                "summary": agent_props.get("summary", "Workflow completed successfully."),
                "output_destination": agent_props.get("output_destination", ""),
                "notify_on_complete": agent_props.get("notify_on_complete", True),
            },
            "logs": [
                "Workflow End reached.",
                f"Collecting outputs from {n_agents} upstream agent(s)…",
                "Aggregating results…",
                "Final workflow data written to output collection.",
                "Execution complete.",
            ],
        },
        AgentType.AUTOMATIC: {
            "input":  {"records": random.randint(100, 5000), "source": "api"},
            "output": {"processed": random.randint(90, 4990), "errors": random.randint(0, 5)},
            "logs": [
                "Initialising agent…",
                f"Processing {random.randint(100, 5000)} records…",
                "Validation checks passed.",
                f"Completed in {duration} ms.",
            ],
        },
        AgentType.ROLE_BASED: {
            "input":  {"role": "compliance", "items": random.randint(1, 10)},
            "output": {"decisions": random.randint(1, 10), "escalated": 0},
            "logs": [
                "Checking role-based routing rules…",
                "Assigning to compliance team.",
                "Decision recorded.",
            ],
        },
        AgentType.CONDITIONAL: {
            "input":  {"condition": "status == 'approved'", "evaluated": True},
            "output": {"branch": "success", "forwarded_records": random.randint(10, 200)},
            "logs": [
                "Evaluating condition…",
                "Condition TRUE – routing to success branch.",
            ],
        },
        AgentType.PARALLEL: {
            "input":  {"tasks": n_tasks},
            "output": {"completed": n_tasks, "failed": 0, "duration_saved_ms": random.randint(200, 1500)},
            "logs": [
                f"Spawning {n_tasks} parallel sub-tasks…",
                "All sub-tasks finished.",
                "Results merged.",
            ],
        },
        AgentType.PROMPT_AGENT: {
            "input":  {"system_prompt": "You are a helpful assistant specialized in {{domain}}.",
                       "user_prompt": "{{task_description}}",
                       "variables": {"domain": "data analysis", "task_description": "Summarise the key trends."}},
            "output": {"response": "Key trends identified: growth in Q3, anomaly in region 4.",
                       "tokens_used": tokens, "model": "llama-3.3-70b-versatile"},
            "logs": [
                "Loading system prompt template…",
                "Injecting variables into prompt…",
                "Calling LLM (llama-3.3-70b-versatile)…",
                f"Response received — {tokens} tokens used.",
                "Output formatted successfully.",
            ],
        },
        AgentType.REACT_AGENT: {
            "input":  {"goal": "Research latest trends and compile a summary.",
                       "available_tools": ["web_search", "rest_api_caller"]},
            "output": {"reasoning_steps": n_iters,
                       "tools_invoked": random.randint(1, n_iters),
                       "final_answer": "Summary compiled after web search and API lookups."},
            "logs": [
                "Thought: Understanding the research goal…",
                "Act: Calling Web Search tool…",
                "Observation: Found 5 relevant results.",
                "Thought: Need more data — calling REST API…",
                "Observation: API returned structured data.",
                f"Thought: Sufficient context after {n_iters} iterations.",
                "Final answer generated.",
            ],
        },
        AgentType.REFLECTION_AGENT: {
            "input":  {"initial_draft": "Draft output from upstream agent.",
                       "critique_prompt": "Rate quality 1–10 and suggest improvements."},
            "output": {"iterations": n_iters, "quality_score": quality,
                       "improved_output": "Refined output after self-critique.",
                       "improvement_summary": f"Quality raised from {round(quality-1.5,1)} → {quality} in {n_iters} passes."},
            "logs": [
                "Generating initial output…",
                f"Self-critique pass 1 — score: {round(quality-1.5,1)}/10",
                "Weaknesses: verbosity, missing examples.",
                "Revising output…",
                f"Self-critique pass 2 — score: {quality}/10 — threshold met.",
                "Reflection complete.",
            ],
        },
        AgentType.GUARDRAILS: {
            "input":  {"content_length": random.randint(50, 800),
                       "rules": ["no_pii", "safe_content", "max_length:4096"]},
            "output": {"passed": True, "violations": [],
                       "pii_entities_redacted": 0,
                       "toxicity_score": round(random.uniform(0.0, 0.05), 3)},
            "logs": [
                "Running guardrail checks…",
                "PII scan: no entities detected.",
                "Toxicity check: score 0.02 — passed.",
                "Schema validation: passed.",
                "Content length: within limits.",
                "All guardrail checks passed ✓",
            ],
        },
        AgentType.ORCHESTRATOR: {
            "input":  {"task": "Complex multi-step analysis", "strategy": "llm_decomposition"},
            "output": {"sub_tasks_created": n_agents, "sub_tasks_completed": n_agents,
                       "results_merged": True, "merge_strategy": "reduce"},
            "logs": [
                "Decomposing task using LLM strategy…",
                f"Created {n_agents} sub-tasks.",
                f"Dispatching to {n_agents} specialist agents…",
                "Awaiting sub-agent completions…",
                f"All {n_agents} sub-tasks completed.",
                "Merging outputs via reduce strategy…",
                "Orchestration complete.",
            ],
        },
        AgentType.SUPERVISOR: {
            "input":  {"agents_monitored": n_agents, "routing_policy": "round_robin",
                       "task_batch_size": random.randint(5, 20)},
            "output": {"tasks_routed": random.randint(5, 20), "failures_caught": 0,
                       "retries_triggered": 0, "agents_healthy": n_agents},
            "logs": [
                f"Supervisor monitoring {n_agents} agents…",
                "Heartbeat check: all agents healthy.",
                "Routing task batch via round_robin policy…",
                "No failures detected.",
                "Supervision cycle complete.",
            ],
        },
    }

    data = step_data.get(atype, step_data[AgentType.AUTOMATIC])

    # Start and End lifecycle agents always succeed; others have 5% random failure
    if atype in (AgentType.START, AgentType.END):
        status = ExecutionStatus.COMPLETED
    else:
        status = ExecutionStatus.FAILED if random.random() < 0.05 else ExecutionStatus.COMPLETED

    return StepResult(
        node_id=node.id,
        agent_name=node.data.get("name") or (agent.name if agent else "Unknown Agent"),
        node_kind="agent",
        status=status,
        started_at=started,
        completed_at=started + timedelta(milliseconds=duration),
        input=data["input"],
        output=data["output"] if status == ExecutionStatus.COMPLETED else {},
        logs=data["logs"] + (["ERROR: step failed unexpectedly."] if status == ExecutionStatus.FAILED else []),
        duration_ms=duration,
    )


def _fake_tool_step(node) -> StepResult:
    """Simulate execution of a tool node."""
    tool_type = node.data.get("toolType", "api_call")
    duration = random.randint(200, 1800)
    started = datetime.utcnow()
    props = node.data.get("properties") or {}

    step_data = {
        "api_call": {
            "input":  {"method": props.get("method", "GET"), "url": props.get("url", "https://api.example.com"), "headers": props.get("headers", {})},
            "output": {"status_code": 200, "response_time_ms": duration, "body": {"result": "ok", "records": random.randint(1, 500)}},
            "logs": [
                f"Sending {props.get('method', 'GET')} request to {props.get('url', 'https://api.example.com')}…",
                "Connection established.",
                f"Response received: 200 OK in {duration}ms.",
                "Response body parsed successfully.",
            ],
        },
        "data_transform": {
            "input":  {"records": random.randint(50, 2000), "input_format": props.get("input_format", "json")},
            "output": {"records_out": random.randint(50, 2000), "output_format": props.get("output_format", "json"), "fields_mapped": random.randint(3, 12)},
            "logs": [
                f"Reading {props.get('input_format', 'json').upper()} input…",
                "Applying mapping rules…",
                f"Transformed {random.randint(50, 2000)} records.",
                f"Output written as {props.get('output_format', 'json').upper()}.",
            ],
        },
        "notification": {
            "input":  {"recipients": [props.get("from_address", "system@example.com")], "subject": "Workflow Notification"},
            "output": {"sent": True, "message_id": f"msg-{random.randint(1000, 9999)}", "delivery_ms": duration},
            "logs": [
                f"Connecting to {props.get('smtp_server', 'smtp.gmail.com')}…",
                "SMTP handshake complete.",
                "Message composed and queued.",
                f"Email delivered in {duration}ms.",
            ],
        },
        "database": {
            "input":  {"query": props.get("query_template", "SELECT * FROM table"), "timeout": props.get("timeout", 60)},
            "output": {"rows_returned": random.randint(1, 1000), "execution_time_ms": duration, "affected_rows": 0},
            "logs": [
                "Connecting to database…",
                "Connection pool acquired.",
                "Executing query…",
                f"Query returned {random.randint(1, 1000)} rows in {duration}ms.",
            ],
        },
        "file_io": {
            "input":  {"path": props.get("path", "/data/input.csv"), "mode": props.get("mode", "read")},
            "output": {"bytes_read": random.randint(1024, 1048576), "lines": random.randint(10, 5000)},
            "logs": [
                f"Opening file: {props.get('path', '/data/input.csv')}",
                f"Reading {random.randint(10, 5000)} lines…",
                "File parsed successfully.",
            ],
        },
        "ai_inference": {
            "input":  {"model": props.get("model", "llama-3.3-70b-versatile"), "prompt_tokens": random.randint(50, 400)},
            "output": {"completion_tokens": random.randint(80, 600), "total_tokens": random.randint(130, 1000), "confidence": round(random.uniform(0.82, 0.99), 3)},
            "logs": [
                f"Loading model: {props.get('model', 'llama-3.3-70b-versatile')}",
                "Tokenising input…",
                "Running inference…",
                f"Inference complete — {random.randint(130, 1000)} tokens used.",
            ],
        },
        "approval": {
            "input":  {"policy": props.get("policy", "auto_approve"), "threshold": props.get("threshold", 0.8)},
            "output": {"decision": "approved", "confidence": round(random.uniform(0.85, 0.99), 3), "policy_applied": props.get("policy", "auto_approve")},
            "logs": [
                "Evaluating approval policy…",
                f"Policy '{props.get('policy', 'auto_approve')}' matched.",
                "Decision: Approved.",
            ],
        },
        "webhook": {
            "input":  {"url": props.get("url", "https://hooks.example.com/trigger"), "event": props.get("event_type", "workflow.step")},
            "output": {"delivered": True, "http_status": 200, "latency_ms": duration},
            "logs": [
                f"Dispatching webhook to {props.get('url', 'https://hooks.example.com/trigger')}…",
                "Payload serialised.",
                f"Webhook acknowledged: 200 OK ({duration}ms).",
            ],
        },
    }

    data = step_data.get(tool_type, step_data["api_call"])
    status = ExecutionStatus.FAILED if random.random() < 0.04 else ExecutionStatus.COMPLETED

    return StepResult(
        node_id=node.id,
        agent_name=node.data.get("name", "Tool"),
        node_kind="tool",
        status=status,
        started_at=started,
        completed_at=started + timedelta(milliseconds=duration),
        input=data["input"],
        output=data["output"] if status == ExecutionStatus.COMPLETED else {},
        logs=data["logs"] + (["ERROR: tool execution failed."] if status == ExecutionStatus.FAILED else []),
        duration_ms=duration,
    )


def _validate_start_end_constraints(workflow):
    """Enforce Start/End structural rules before execution."""
    start_nodes = [n for n in workflow.nodes if n.data.get("type") == "start"]
    end_nodes   = [n for n in workflow.nodes if n.data.get("type") == "end"]

    if len(start_nodes) > 1:
        raise HTTPException(status_code=400, detail="Workflow can only have one Start agent")
    if len(end_nodes) > 1:
        raise HTTPException(status_code=400, detail="Workflow can only have one End agent")

    start_ids = {n.id for n in start_nodes}
    end_ids   = {n.id for n in end_nodes}

    for e in workflow.edges:
        if e.target in start_ids:
            raise HTTPException(status_code=400,
                detail="Start agent cannot be the target of any connection")
        if e.source in end_ids:
            raise HTTPException(status_code=400,
                detail="End agent cannot be the source of any connection")


def execute_workflow(workflow_id: str, trigger_context: Optional[Dict[str, Any]] = None) -> ExecutionRun:
    """Run a workflow and return an ExecutionRun. Can be called from the public
    /run endpoint (manual) or from /triggers/* endpoints (webhook/cron/sheet/email).

    `trigger_context` is merged into exec_context["wf"]["trigger"] and surfaced
    in the Start node's output so downstream agents can consume it.
    """
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflows_db[workflow_id]
    if not workflow.nodes:
        raise HTTPException(status_code=400, detail="Workflow has no nodes to execute")

    _validate_start_end_constraints(workflow)
    ordered_nodes = _topo_sort(workflow.nodes, workflow.edges)

    # ── Observability: trace the entire run ───────────────
    trace_info = obs.start_trace(
        f"workflow.run: {workflow.name}",
        source="workflow",
        attributes={
            "workflow.id": workflow_id,
            "workflow.name": workflow.name,
            "node_count": len(workflow.nodes),
        },
    )
    run_trace_id = trace_info["trace_id"]
    root_span = trace_info["root_span_id"]
    obs.log(
        "info",
        f"Starting workflow run for '{workflow.name}' ({len(ordered_nodes)} steps)",
        source="workflow", logger="execution",
        trace_id=run_trace_id, workflow_id=workflow_id,
    )

    # ── Initialize runtime data model instance ────────────
    data_model_instance: dict = {}
    assoc = next(
        (a for a in workflow_associations_db.values() if a.workflow_id == workflow_id),
        None,
    )
    if assoc and assoc.data_model_id and assoc.data_model_id in data_models_db:
        data_model_instance = _create_data_model_instance(
            data_models_db[assoc.data_model_id]
        )

    # ── Execution context ──────────────────────────────────
    exec_context: dict = {
        "wf": {"status": "running", "token_limit": 4096, "timetaken": 0},
        "tool_outputs": {},
        "data_model": data_model_instance,
    }
    if trigger_context:
        exec_context["wf"]["trigger"] = trigger_context

    steps: List[StepResult] = []
    failed = False
    elapsed_ms = 0

    for node in ordered_nodes:
        node_name = node.data.get("name", "step")
        span_id = obs.add_span(
            run_trace_id,
            f"{node.node_kind}: {node_name}",
            parent_span_id=root_span,
            attributes={"node.id": node.id, "node.kind": node.node_kind},
        )
        if node.node_kind == "tool":
            step = _fake_tool_step(node)
            # Publish tool output into context for downstream references
            if step.status == ExecutionStatus.COMPLETED:
                tool_key = node.data.get("name", "").replace(" ", "_")
                exec_context["tool_outputs"][tool_key] = step.output
        else:
            agent = _agent_from_node(node)

            # ── Resolve invoke input parameters ───────────
            invoke_cfg = node.data.get("invoke") or {}
            input_params = invoke_cfg.get("input_parameters", [])
            output_params = invoke_cfg.get("output_parameters", [])

            resolved_inputs: dict = {}
            for param in input_params:
                pname = param.get("name", "").strip()
                if not pname:
                    continue
                resolved_inputs[pname] = _resolve_value(
                    param.get("value_type", "constant"),
                    param.get("value", ""),
                    exec_context,
                )

            step = _fake_step(node, agent)
            step.invoke_inputs = resolved_inputs

            # Surface trigger payload through the Start node so downstream
            # agents/tools can consume it via `{{wf.trigger.*}}`.
            if agent.type == AgentType.START and trigger_context:
                step.input = {**step.input, "trigger": trigger_context}
                step.output = {**step.output, "trigger": trigger_context}
                ttype = trigger_context.get("type", "manual")
                tname = trigger_context.get("name") or ttype
                step.logs.insert(1, f"Trigger: {ttype} ({tname}) fired this run.")

            if resolved_inputs:
                step.logs.insert(
                    0,
                    f"Invoke inputs resolved: {list(resolved_inputs.keys())}",
                )

            # ── Map output parameters to data model ───────
            resolved_outputs: dict = {}
            if step.status == ExecutionStatus.COMPLETED and output_params:
                agent_key = node.data.get("name", "").replace(" ", "_")
                # Publish agent output for downstream tool references
                exec_context["tool_outputs"][agent_key] = step.output

                for param in output_params:
                    pname = param.get("name", "").strip()
                    ptype = param.get("value_type", "constant")
                    ptarget = param.get("value", "")
                    if not pname:
                        continue

                    # Capture value from step output by parameter name
                    captured = step.output.get(pname, "")
                    resolved_outputs[pname] = captured

                    # Persist to data model instance when target is data_model
                    if ptype == "data_model" and ptarget:
                        match = re.match(
                            r"\{\{([^.}]+)\.([^}]+)\}\}", ptarget
                        )
                        if match:
                            entity_name, field_name = match.group(1), match.group(2)
                            if entity_name in data_model_instance:
                                data_model_instance[entity_name][field_name] = captured

                exec_context["data_model"] = data_model_instance

                if resolved_outputs:
                    step.logs.append(
                        f"Invoke outputs captured: {list(resolved_outputs.keys())}"
                    )

            step.invoke_outputs = resolved_outputs

        steps.append(step)
        elapsed_ms += step.duration_ms or 0
        exec_context["wf"]["timetaken"] = elapsed_ms

        # ── Observability: close per-node span + emit log ─
        span_status = "ok"
        if step.status == ExecutionStatus.FAILED:
            span_status = "error"
        elif step.status == ExecutionStatus.PENDING:
            span_status = "pending"
        obs.end_span(
            run_trace_id, span_id, status=span_status,
            attributes={"duration_ms": step.duration_ms or 0, "step.status": step.status.value},
        )
        log_level = "error" if step.status == ExecutionStatus.FAILED else "info"
        obs.log(
            log_level,
            f"Step '{step.agent_name}' [{node.node_kind}] → {step.status.value} ({step.duration_ms or 0}ms)",
            source="workflow", logger="execution",
            trace_id=run_trace_id, span_id=span_id,
            workflow_id=workflow_id,
            extra={"node_id": node.id, "duration_ms": step.duration_ms or 0},
        )
        obs.record_metric(
            "workflow.step.duration_ms", step.duration_ms or 0,
            labels={"workflow_id": workflow_id, "kind": node.node_kind, "status": step.status.value},
        )

        if step.status == ExecutionStatus.FAILED:
            failed = True
            break

    # Mark any nodes that weren't reached as skipped
    reached_ids = {s.node_id for s in steps}
    for node in ordered_nodes:
        if node.id not in reached_ids:
            steps.append(StepResult(
                node_id=node.id,
                agent_name=node.data.get("name") or "Unknown",
                node_kind=node.node_kind if hasattr(node, "node_kind") else "agent",
                status=ExecutionStatus.SKIPPED,
                started_at=datetime.utcnow(),
                input={}, output={},
                logs=["Step skipped due to upstream failure."],
                duration_ms=0,
            ))

    total_ms = sum(s.duration_ms or 0 for s in steps)
    exec_context["wf"]["status"] = "failed" if failed else "completed"
    exec_context["wf"]["timetaken"] = total_ms

    run = ExecutionRun(
        workflow_id=workflow_id,
        status=ExecutionStatus.FAILED if failed else ExecutionStatus.COMPLETED,
        steps=steps,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow() + timedelta(milliseconds=total_ms),
        total_duration_ms=total_ms,
        data_model_instance=data_model_instance,
    )
    executions_db[run.id] = run

    # ── Observability: close run trace + final log ───────
    obs.end_trace(run_trace_id, status="error" if failed else "ok")
    obs.log(
        "error" if failed else "info",
        f"Workflow run {'FAILED' if failed else 'completed'}: '{workflow.name}' in {total_ms}ms ({len(steps)} steps)",
        source="workflow", logger="execution",
        trace_id=run_trace_id, workflow_id=workflow_id,
        extra={"run_id": run.id, "total_ms": total_ms, "failed": failed},
    )
    obs.record_metric(
        "workflow.run.duration_ms", total_ms,
        labels={"workflow_id": workflow_id, "status": run.status.value},
    )
    obs.record_metric("workflow.runs", 1, labels={"status": run.status.value})

    return run


@router.post("/{workflow_id}/run", response_model=ExecutionRun)
async def run_execution(
    workflow_id: str,
    trigger: Optional[Dict[str, Any]] = Body(default=None),
):
    """Manual workflow run. `trigger` body is optional — when present it is
    surfaced through the Start node and available via {{wf.trigger.*}}."""
    return execute_workflow(workflow_id, trigger_context=trigger)


@router.get("", response_model=List[ExecutionRun])
async def list_executions(workflow_id: Optional[str] = None):
    runs = list(executions_db.values())
    if workflow_id:
        runs = [r for r in runs if r.workflow_id == workflow_id]
    return sorted(runs, key=lambda r: r.started_at, reverse=True)


@router.get("/{execution_id}", response_model=ExecutionRun)
async def get_execution(execution_id: str):
    if execution_id not in executions_db:
        raise HTTPException(status_code=404, detail="Execution not found")
    return executions_db[execution_id]

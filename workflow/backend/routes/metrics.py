"""Dashboard metrics and reports endpoints."""
import random
import hashlib
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from typing import Optional

from db import workflows_db, executions_db, tools_db, agents_db, users_db, audit_logs
from routes.auth import get_current_user

router = APIRouter()


def _fake_trend(base: int, days: int = 7):
    """Generate plausible daily counts for a sparkline."""
    result = []
    for i in range(days):
        result.append({"day": (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%m/%d"), "count": max(0, base + random.randint(-base // 3, base // 2))})
    return result


@router.get("/dashboard")
def dashboard(
    workflow_id: str = Query(""),
    actor=Depends(get_current_user),
):
    if workflow_id:
        wf_single = workflows_db.get(workflow_id)
        wf_scope = [wf_single] if wf_single else []
        total_wf = len(wf_scope)
        active_wf = sum(1 for w in wf_scope if w.status.value == "active")
        draft_wf = sum(1 for w in wf_scope if w.status.value == "draft")
        exec_scope = [e for e in executions_db.values() if e.workflow_id == workflow_id]
    else:
        total_wf = len(workflows_db)
        active_wf = sum(1 for w in workflows_db.values() if w.status.value == "active")
        draft_wf = sum(1 for w in workflows_db.values() if w.status.value == "draft")
        exec_scope = list(executions_db.values())

    total_exec = len(exec_scope)
    completed_exec = sum(1 for e in exec_scope if e.status.value == "completed")
    failed_exec = sum(1 for e in exec_scope if e.status.value == "failed")
    running_exec = sum(1 for e in exec_scope if e.status.value == "running")

    # Duration stats
    durations = [e.total_duration_ms for e in exec_scope if e.total_duration_ms]
    avg_duration = int(sum(durations) / len(durations)) if durations else 0

    # SLA: treat executions completing within 30s as SLA-compliant
    sla_threshold = 30000
    sla_compliant = sum(1 for d in durations if d <= sla_threshold)
    sla_pct = round(sla_compliant / len(durations) * 100) if durations else 100

    # Token consumption – simulate per-execution token usage
    tokens_per_exec = 1200
    total_tokens = total_exec * tokens_per_exec
    today_tokens = max(0, random.randint(800, 3000))

    return {
        "workflows": {"total": total_wf, "active": active_wf, "draft": draft_wf},
        "executions": {
            "total": total_exec,
            "completed": completed_exec,
            "failed": failed_exec,
            "running": running_exec,
            "success_rate": round(completed_exec / total_exec * 100) if total_exec else 0,
        },
        "performance": {
            "avg_duration_ms": avg_duration,
            "sla_compliance_pct": sla_pct,
        },
        "tokens": {
            "total_consumed": total_tokens,
            "today": today_tokens,
            "monthly_budget": 500000,
            "usage_pct": round(total_tokens / 500000 * 100, 1),
        },
        "library": {
            "tools": len(tools_db),
            "agents": len(agents_db),
        },
        "users": {
            "total": len(users_db),
            "active": sum(1 for u in users_db.values() if u.is_active),
        },
        "trends": {
            "executions_7d": _fake_trend(max(total_exec // 7, 2)),
            "tokens_7d": _fake_trend(today_tokens),
        },
    }


def _seeded_int(item_id: str, min_val: int, range_size: int) -> int:
    """Return a deterministic pseudo-random int seeded by item_id."""
    return int(hashlib.md5(item_id.encode()).hexdigest(), 16) % range_size + min_val


@router.get("/dashboard/detail")
def dashboard_detail(
    filter_name: str = Query("Workflows", alias="filter"),
    tab: str = Query("total_workflows"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str = Query("", description="Global search"),
    sort_by: str = Query(""),
    sort_dir: str = Query("asc"),
    status: str = Query(""),
    role: str = Query(""),
    review_status_filter: str = Query("", alias="review_status"),
    sla_breach: str = Query(""),
    workflow_id: str = Query(""),
    actor=Depends(get_current_user),
):
    rows = []
    aggregations = {}

    # ── Workflows ────────────────────────────────────────────────────────────
    if filter_name == "Workflows":
        wf_list = list(workflows_db.values())

        # Workflow filter
        if workflow_id:
            wf_list = [w for w in wf_list if w.id == workflow_id]

        # Tab filter
        if tab == "active_workflows":
            wf_list = [w for w in wf_list if w.status.value == "active"]
        elif tab == "draft_workflows":
            wf_list = [w for w in wf_list if w.status.value == "draft"]

        # Context filter
        if status:
            wf_list = [w for w in wf_list if w.status.value == status]

        # Search
        if search:
            sl = search.lower()
            wf_list = [w for w in wf_list if sl in w.name.lower() or sl in w.description.lower()]

        # Build rows
        for wf in wf_list:
            execs = [e for e in executions_db.values() if e.workflow_id == wf.id]
            completed = [e for e in execs if e.status.value == "completed"]
            durations = [e.total_duration_ms for e in execs if e.total_duration_ms]
            avg_dur = int(sum(durations) / len(durations)) if durations else 0
            succ = int(len(completed) / len(execs) * 100) if execs else 0
            last_run = max((e.started_at for e in execs), default=None)
            rows.append({
                "id": wf.id,
                "name": wf.name,
                "status": wf.status.value,
                "version": "1.0",
                "created_by": "System",
                "last_updated": wf.updated_at.isoformat(),
                "last_run": last_run.isoformat() if last_run else None,
                "total_executions": len(execs),
                "success_rate": succ,
                "avg_duration": avg_dur,
                "tags": wf.tags,
            })

        # Sort
        if sort_by:
            reverse = sort_dir == "desc"
            rows.sort(key=lambda r: (r.get(sort_by) or 0) if isinstance(r.get(sort_by), (int, float)) else str(r.get(sort_by) or ""), reverse=reverse)

        # Aggregations (before pagination)
        total_count = len(rows)
        active_count = sum(1 for r in rows if r["status"] == "active")
        failed_count = sum(1 for r in rows if r["status"] not in ("active", "draft"))
        avg_dur_vals = [r["avg_duration"] for r in rows if r["avg_duration"]]
        avg_duration_s = round(sum(avg_dur_vals) / len(avg_dur_vals) / 1000, 2) if avg_dur_vals else 0
        succ_vals = [r["success_rate"] for r in rows]
        success_pct = round(sum(succ_vals) / len(succ_vals), 1) if succ_vals else 0
        aggregations = {"total_count": total_count, "active_count": active_count, "failed_count": failed_count, "avg_duration_s": avg_duration_s, "success_pct": success_pct, "token_usage": 0}

    # ── Executions ───────────────────────────────────────────────────────────
    elif filter_name == "Executions":
        exec_list = list(executions_db.values())

        # Tab filter
        if tab == "running":
            exec_list = [e for e in exec_list if e.status.value == "running"]
        elif tab == "completed":
            exec_list = [e for e in exec_list if e.status.value == "completed"]
        elif tab == "failed":
            exec_list = [e for e in exec_list if e.status.value == "failed"]

        # Workflow filter
        if workflow_id:
            exec_list = [e for e in exec_list if e.workflow_id == workflow_id]

        # Context filters
        if status:
            exec_list = [e for e in exec_list if e.status.value == status]
        if sla_breach == "yes":
            exec_list = [e for e in exec_list if (e.total_duration_ms or 0) > 30000]
        elif sla_breach == "no":
            exec_list = [e for e in exec_list if (e.total_duration_ms or 0) <= 30000]

        # Search
        if search:
            sl = search.lower()
            filtered = []
            for e in exec_list:
                wf = workflows_db.get(e.workflow_id)
                wf_name = wf.name if wf else ""
                if sl in e.id.lower() or sl in wf_name.lower():
                    filtered.append(e)
            exec_list = filtered

        # Build rows
        for e in exec_list:
            wf = workflows_db.get(e.workflow_id)
            wf_name = wf.name if wf else e.workflow_id
            dur = e.total_duration_ms or 0
            tok = _seeded_int(e.id, 800, 1200)
            rows.append({
                "id": e.id,
                "workflow_name": wf_name,
                "status": e.status.value,
                "started_at": e.started_at.isoformat(),
                "ended_at": e.completed_at.isoformat() if e.completed_at else None,
                "duration": dur,
                "tokens_used": tok,
                "sla_status": "breach" if dur > 30000 else "ok",
            })

        # Sort
        if sort_by:
            reverse = sort_dir == "desc"
            rows.sort(key=lambda r: (r.get(sort_by) or 0) if isinstance(r.get(sort_by), (int, float)) else str(r.get(sort_by) or ""), reverse=reverse)

        # Aggregations
        total_count = len(rows)
        active_count = sum(1 for r in rows if r["status"] == "running")
        failed_count = sum(1 for r in rows if r["status"] == "failed")
        dur_vals = [r["duration"] for r in rows if r["duration"]]
        avg_duration_s = round(sum(dur_vals) / len(dur_vals) / 1000, 2) if dur_vals else 0
        completed_count = sum(1 for r in rows if r["status"] == "completed")
        success_pct = round(completed_count / total_count * 100, 1) if total_count else 0
        aggregations = {"total_count": total_count, "active_count": active_count, "failed_count": failed_count, "avg_duration_s": avg_duration_s, "success_pct": success_pct, "token_usage": sum(r["tokens_used"] for r in rows)}

    # ── Performance ──────────────────────────────────────────────────────────
    elif filter_name == "Performance":
        wf_list = list(workflows_db.values())

        # Workflow filter
        if workflow_id:
            wf_list = [w for w in wf_list if w.id == workflow_id]

        # Search
        if search:
            sl = search.lower()
            wf_list = [w for w in wf_list if sl in w.name.lower()]

        for wf in wf_list:
            execs = [e for e in executions_db.values() if e.workflow_id == wf.id]
            durations = [e.total_duration_ms for e in execs if e.total_duration_ms]
            avg_dur = int(sum(durations) / len(durations)) if durations else _seeded_int(wf.id, 500, 9500)
            completed = [e for e in execs if e.status.value == "completed"]
            failed = [e for e in execs if e.status.value == "failed"]
            total_runs = len(execs) if execs else _seeded_int(wf.id + "runs", 1, 50)
            failed_runs = len(failed) if failed else _seeded_int(wf.id + "fail", 0, 10)
            succ_rate = int(len(completed) / len(execs) * 100) if execs else _seeded_int(wf.id + "succ", 70, 30)
            sla_ok = sum(1 for d in durations if d <= 30000)
            sla_pct = int(sla_ok / len(durations) * 100) if durations else _seeded_int(wf.id + "sla", 60, 40)
            rows.append({
                "id": wf.id,
                "name": wf.name,
                "avg_duration": avg_dur,
                "avg_duration_s": round(avg_dur / 1000, 2),
                "sla_compliance_pct": sla_pct,
                "success_rate": succ_rate,
                "total_runs": total_runs,
                "failed_runs": failed_runs,
            })

        # Default sort by tab
        if not sort_by:
            if tab == "avg_duration":
                rows.sort(key=lambda r: r["avg_duration"], reverse=True)
            elif tab == "sla_compliance":
                rows.sort(key=lambda r: r["sla_compliance_pct"])
            elif tab == "success_rate":
                rows.sort(key=lambda r: r["success_rate"])
        else:
            reverse = sort_dir == "desc"
            rows.sort(key=lambda r: (r.get(sort_by) or 0) if isinstance(r.get(sort_by), (int, float)) else str(r.get(sort_by) or ""), reverse=reverse)

        # Aggregations
        total_count = len(rows)
        avg_dur_s = round(sum(r["avg_duration_s"] for r in rows) / total_count, 2) if total_count else 0
        avg_sla = round(sum(r["sla_compliance_pct"] for r in rows) / total_count, 1) if total_count else 0
        avg_succ = round(sum(r["success_rate"] for r in rows) / total_count, 1) if total_count else 0
        aggregations = {"total_count": total_count, "active_count": 0, "failed_count": 0, "avg_duration_s": avg_dur_s, "success_pct": avg_succ, "token_usage": 0}

    # ── Tokens ───────────────────────────────────────────────────────────────
    elif filter_name == "Tokens":
        if tab == "token_by_agent":
            source_list = [(a.id, a.name, "agent", a.description) for a in agents_db.values()]
        else:
            source_list = [(w.id, w.name, "workflow", w.description) for w in workflows_db.values()]

        # Workflow filter (only applies to workflow-scoped tabs)
        if workflow_id and tab != "token_by_agent":
            source_list = [(i, n, t, d) for (i, n, t, d) in source_list if i == workflow_id]

        # Search
        if search:
            sl = search.lower()
            source_list = [(i, n, t, d) for (i, n, t, d) in source_list if sl in n.lower() or sl in d.lower()]

        for (item_id, name, itype, desc) in source_list:
            tokens = _seeded_int(item_id + "tok", 500, 14500)
            rows.append({
                "id": item_id,
                "name": name,
                "type": itype,
                "tokens_used": tokens,
                "cost_usd": round(tokens * 0.000002, 6),
                "pct_budget": round(tokens / 500000 * 100, 2),
            })

        # Sort
        if sort_by:
            reverse = sort_dir == "desc"
            rows.sort(key=lambda r: (r.get(sort_by) or 0) if isinstance(r.get(sort_by), (int, float)) else str(r.get(sort_by) or ""), reverse=reverse)
        else:
            rows.sort(key=lambda r: r["tokens_used"], reverse=True)

        # Aggregations
        total_count = len(rows)
        token_total = sum(r["tokens_used"] for r in rows)
        avg_tokens = round(token_total / total_count) if total_count else 0
        aggregations = {"total_count": total_count, "active_count": avg_tokens, "failed_count": 0, "avg_duration_s": 0, "success_pct": 0, "token_usage": token_total}

    # ── Trends ───────────────────────────────────────────────────────────────
    elif filter_name == "Trends":
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        days = [(today - timedelta(days=13 - i)) for i in range(14)]

        def count_for_day(day, exec_status=None):
            day_end = day + timedelta(days=1)
            return sum(
                1 for e in executions_db.values()
                if day <= e.started_at < day_end and (exec_status is None or e.status.value == exec_status)
            )

        def sim_for_day(day, seed_extra=""):
            seed = day.strftime("%Y%m%d") + seed_extra
            return _seeded_int(seed, 5, 95)

        if tab == "execution_trend":
            counts = [count_for_day(d) for d in days]
        elif tab == "failure_trend":
            counts = [count_for_day(d, "failed") for d in days]
        elif tab == "usage_trend":
            counts = [sim_for_day(d, "usage") for d in days]
        elif tab == "performance_trend":
            counts = [sim_for_day(d, "perf") * 100 for d in days]  # avg ms as int
        else:
            counts = [count_for_day(d) for d in days]

        running_total = 0
        for i, (day, cnt) in enumerate(zip(days, counts)):
            prev = counts[i - 1] if i > 0 else cnt
            change_pct = round((cnt - prev) / prev * 100, 1) if prev else 0
            running_total += cnt
            rows.append({
                "id": day.strftime("%Y-%m-%d"),
                "day": day.strftime("%Y-%m-%d"),
                "count": cnt,
                "change_pct": change_pct,
                "total": running_total,
            })

        total_count = len(rows)
        total_sum = running_total
        aggregations = {"total_count": total_count, "active_count": 0, "failed_count": 0, "avg_duration_s": 0, "success_pct": 0, "token_usage": total_sum}
        # Trends: return all rows, skip pagination
        return {"rows": rows, "total": total_count, "page": 1, "page_size": total_count, "aggregations": aggregations}

    # ── Library ──────────────────────────────────────────────────────────────
    elif filter_name == "Library":
        if tab == "tools":
            source = list(tools_db.values())
            for t in source:
                rows.append({
                    "id": t.id,
                    "name": t.name,
                    "type": t.type.value,
                    "description": t.description,
                    "review_status": t.review_status,
                    "usage_count": _seeded_int(t.id + "use", 0, 50),
                    "created_at": "",
                })
        elif tab == "agents":
            source = list(agents_db.values())
            for a in source:
                rows.append({
                    "id": a.id,
                    "name": a.name,
                    "type": a.type.value,
                    "description": a.description,
                    "review_status": a.review_status,
                    "usage_count": _seeded_int(a.id + "use", 0, 50),
                    "created_at": "",
                })
        else:  # templates
            templates = [w for w in workflows_db.values() if w.is_template]
            for wf in templates:
                rows.append({
                    "id": wf.id,
                    "name": wf.name,
                    "type": "template",
                    "description": wf.description,
                    "review_status": "approved",
                    "usage_count": _seeded_int(wf.id + "use", 0, 20),
                    "created_at": wf.created_at.isoformat(),
                })

        # Context filter: review_status
        if review_status_filter:
            rows = [r for r in rows if r["review_status"] == review_status_filter]

        # Search
        if search:
            sl = search.lower()
            rows = [r for r in rows if sl in r["name"].lower() or sl in r["description"].lower()]

        # Sort
        if sort_by:
            reverse = sort_dir == "desc"
            rows.sort(key=lambda r: (r.get(sort_by) or 0) if isinstance(r.get(sort_by), (int, float)) else str(r.get(sort_by) or ""), reverse=reverse)

        # Aggregations
        total_count = len(rows)
        active_count = sum(1 for r in rows if r["review_status"] == "approved")
        failed_count = sum(1 for r in rows if r["review_status"] == "rejected")
        aggregations = {"total_count": total_count, "active_count": active_count, "failed_count": failed_count, "avg_duration_s": 0, "success_pct": 0, "token_usage": 0}

    # ── Users ────────────────────────────────────────────────────────────────
    elif filter_name == "Users":
        user_list = list(users_db.values())

        # Tab filter
        if tab == "active_users":
            user_list = [u for u in user_list if u.is_active]

        # Context filter: role
        if role:
            user_list = [u for u in user_list if u.role.value == role]

        # Search
        if search:
            sl = search.lower()
            user_list = [u for u in user_list if sl in u.name.lower() or sl in u.email.lower()]

        # Build rows
        for u in user_list:
            user_logs = [l for l in audit_logs if l.user_id == u.id]
            exec_count = sum(1 for l in user_logs if l.action == "execute")
            last_ts = max((l.timestamp for l in user_logs), default=None)
            tok = _seeded_int(u.id + "tok", 1000, 49000)
            rows.append({
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role.value,
                "active_workflows": 0,
                "executions_triggered": exec_count,
                "token_usage": tok,
                "last_active": last_ts.isoformat() if last_ts else None,
                "is_active": u.is_active,
            })

        # Tab-specific sorts
        if tab == "user_activity" and not sort_by:
            rows.sort(key=lambda r: r["executions_triggered"], reverse=True)
        elif tab == "top_consumers" and not sort_by:
            rows.sort(key=lambda r: r["token_usage"], reverse=True)
        elif sort_by:
            reverse = sort_dir == "desc"
            rows.sort(key=lambda r: (r.get(sort_by) or 0) if isinstance(r.get(sort_by), (int, float)) else str(r.get(sort_by) or ""), reverse=reverse)

        # Aggregations
        total_count = len(rows)
        active_count = sum(1 for r in rows if r["is_active"])
        avg_tok = round(sum(r["token_usage"] for r in rows) / total_count) if total_count else 0
        aggregations = {"total_count": total_count, "active_count": active_count, "failed_count": 0, "avg_duration_s": 0, "success_pct": 0, "token_usage": avg_tok}

    # ── Paginate ─────────────────────────────────────────────────────────────
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]

    return {
        "rows": page_rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "aggregations": aggregations,
    }


@router.get("/reports")
def reports(
    report_type: str = Query("workflow_usage"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    actor=Depends(get_current_user),
):
    if report_type == "workflow_usage":
        rows = []
        for wf in list(workflows_db.values())[:20]:
            execs = [e for e in executions_db.values() if e.workflow_id == wf.id]
            rows.append({
                "name": wf.name,
                "id": wf.id,
                "status": wf.status,
                "executions": len(execs),
                "completed": sum(1 for e in execs if e.status == "completed"),
                "failed": sum(1 for e in execs if e.status == "failed"),
                "last_run": max((e.started_at.isoformat() for e in execs), default=None),
            })
        rows.sort(key=lambda r: r["executions"], reverse=True)
        return {"report_type": report_type, "rows": rows, "generated_at": datetime.utcnow().isoformat()}

    if report_type == "agent_performance":
        rows = []
        for ag in list(agents_db.values())[:20]:
            rows.append({
                "name": ag.name,
                "id": ag.id,
                "type": ag.type,
                "avg_duration_ms": random.randint(500, 8000),
                "success_rate": random.randint(88, 100),
                "invocations": random.randint(5, 200),
            })
        return {"report_type": report_type, "rows": rows, "generated_at": datetime.utcnow().isoformat()}

    if report_type == "user_activity":
        rows = []
        for u in list(users_db.values())[:20]:
            user_logs = [l for l in audit_logs if l.user_id == u.id]
            rows.append({
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "actions": len(user_logs),
                "last_active": max((l.timestamp.isoformat() for l in user_logs), default=None),
                "is_active": u.is_active,
            })
        rows.sort(key=lambda r: r["actions"], reverse=True)
        return {"report_type": report_type, "rows": rows, "generated_at": datetime.utcnow().isoformat()}

    if report_type == "token_consumption":
        rows = []
        for wf in list(workflows_db.values())[:10]:
            rows.append({
                "name": wf.name,
                "tokens": random.randint(200, 15000),
                "cost_usd": round(random.uniform(0.01, 0.50), 4),
            })
        rows.sort(key=lambda r: r["tokens"], reverse=True)
        total = sum(r["tokens"] for r in rows)
        return {
            "report_type": report_type,
            "rows": rows,
            "summary": {"total_tokens": total, "total_cost_usd": round(total * 0.000002, 4)},
            "generated_at": datetime.utcnow().isoformat(),
        }

    return {"report_type": report_type, "rows": [], "generated_at": datetime.utcnow().isoformat()}

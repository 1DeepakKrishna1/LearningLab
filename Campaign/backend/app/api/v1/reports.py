"""Reporting endpoints: on-demand export + saved report definitions."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select

from app.core.audit import record_audit
from app.core.deps import CurrentUser, DbSession, require_marketer, require_viewer
from app.models import Report
from app.schemas.analytics import ReportCreate, ReportOut
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/export", dependencies=[Depends(require_viewer)])
def export_report(db: DbSession, fmt: str = Query("csv", pattern=r"^(csv|excel|pdf)$")):
    """Generate and download a campaign performance report in the given format."""
    content, media_type, filename = report_service.generate(db, fmt)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("", response_model=list[ReportOut], dependencies=[Depends(require_viewer)])
def list_reports(db: DbSession):
    return list(db.scalars(select(Report).order_by(Report.created_at.desc())))


@router.post("", response_model=ReportOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_marketer)])
def create_report(db: DbSession, payload: ReportCreate, actor: CurrentUser):
    report = Report(
        name=payload.name, report_type=payload.report_type, fmt=payload.fmt.value,
        schedule=payload.schedule.value, filters=payload.filters, created_by_id=actor.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    record_audit(db, action="report.create", user=actor, entity_type="report", entity_id=report.id)
    return report


@router.post("/{report_id}/run", response_model=ReportOut, dependencies=[Depends(require_viewer)])
def run_report(db: DbSession, report_id: int):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.last_generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report

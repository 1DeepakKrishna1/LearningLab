"""
Report API endpoints.

GET    /reports                     — list reports (optional ?dataset_id filter)
POST   /reports                     — create report
POST   /reports/generate            — auto-generate report from NLP prompt
GET    /reports/{id}                — get report with sections
DELETE /reports/{id}                — delete report
POST   /reports/{id}/generate       — run section queries and populate content
POST   /reports/{id}/sections       — add section
GET    /reports/{id}/export/csv     — export as CSV
GET    /reports/{id}/export/pdf     — export as PDF
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.database import get_db
from app.schemas.report import (
    ReportCreate,
    ReportRead,
    ReportSectionCreate,
    ReportSectionRead,
    ReportUpdate,
)
from app.services.report_service import ReportService

router = APIRouter()


def _http(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.to_dict())


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[ReportRead])
async def list_reports(
    dataset_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    svc = ReportService(db)
    reports = await svc.list_reports(dataset_id=dataset_id)
    return [ReportRead.model_validate(r) for r in reports]


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(payload: ReportCreate, db: AsyncSession = Depends(get_db)):
    try:
        svc = ReportService(db)
        report = await svc.create_report(payload)
        return ReportRead.model_validate(report)
    except AppError as exc:
        raise _http(exc)


@router.post("/generate", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
async def auto_generate_report(
    payload: ReportCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a report and immediately generate all section content.
    Useful for one-shot NLP-driven report generation.
    """
    try:
        svc = ReportService(db)
        report = await svc.create_report(payload)
        report = await svc.generate_report(report.id)
        return ReportRead.model_validate(report)
    except AppError as exc:
        raise _http(exc)


@router.get("/{report_id}", response_model=ReportRead)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    try:
        svc = ReportService(db)
        report = await svc.get_report(report_id)
        return ReportRead.model_validate(report)
    except AppError as exc:
        raise _http(exc)


@router.put("/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: str,
    payload: ReportUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        svc = ReportService(db)
        report = await svc.get_report(report_id)
        if payload.title is not None:
            report.title = payload.title
        if payload.description is not None:
            report.description = payload.description
        await db.flush()
        return ReportRead.model_validate(report)
    except AppError as exc:
        raise _http(exc)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: str, db: AsyncSession = Depends(get_db)):
    try:
        svc = ReportService(db)
        await svc.delete_report(report_id)
    except AppError as exc:
        raise _http(exc)


# ── Generation & Sections ─────────────────────────────────────────────────────

@router.post("/{report_id}/generate", response_model=ReportRead)
async def generate_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Execute all section SQL queries and populate section content."""
    try:
        svc = ReportService(db)
        report = await svc.generate_report(report_id)
        return ReportRead.model_validate(report)
    except AppError as exc:
        raise _http(exc)


@router.post("/{report_id}/sections", response_model=ReportSectionRead, status_code=status.HTTP_201_CREATED)
async def add_section(
    report_id: str,
    payload: ReportSectionCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        svc = ReportService(db)
        section = await svc.add_section(report_id, payload)
        return ReportSectionRead.model_validate(section)
    except AppError as exc:
        raise _http(exc)


# ── Exports ───────────────────────────────────────────────────────────────────

@router.get("/{report_id}/export/csv")
async def export_csv(report_id: str, db: AsyncSession = Depends(get_db)):
    try:
        svc = ReportService(db)
        csv_bytes = await svc.export_csv(report_id)
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.csv"'},
        )
    except AppError as exc:
        raise _http(exc)


@router.get("/{report_id}/export/pdf")
async def export_pdf(report_id: str, db: AsyncSession = Depends(get_db)):
    try:
        svc = ReportService(db)
        pdf_bytes = await svc.export_pdf(report_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'},
        )
    except AppError as exc:
        raise _http(exc)
    except Exception as exc:
        logger.exception("pdf_export_error", report_id=report_id, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail={"error": "PDF generation failed.", "detail": str(exc), "code": "PDF_ERROR"},
        )

"""
Dashboard API endpoints.

GET    /dashboards                  — list all dashboards
POST   /dashboards                  — create dashboard
POST   /dashboards/generate         — generate dashboard from NLP prompt
GET    /dashboards/{id}             — get dashboard with widgets
PUT    /dashboards/{id}             — update dashboard metadata
DELETE /dashboards/{id}             — delete dashboard

POST   /dashboards/{id}/widgets     — add widget
PUT    /dashboards/{id}/widgets/{wid} — update widget
DELETE /dashboards/{id}/widgets/{wid} — delete widget
POST   /dashboards/{id}/widgets/{wid}/data — execute widget query & return data
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.database import execute_dataset_query, get_db
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardRead,
    DashboardUpdate,
    NLPDashboardRequest,
    WidgetCreate,
    WidgetRead,
    WidgetUpdate,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


def _http(exc: AppError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.to_dict())


# ── Dashboard CRUD ────────────────────────────────────────────────────────────

@router.get("", response_model=List[DashboardRead])
async def list_dashboards(db: AsyncSession = Depends(get_db)):
    svc = DashboardService(db)
    dashboards = await svc.list_dashboards()
    return [DashboardRead.model_validate(d) for d in dashboards]


@router.post("", response_model=DashboardRead, status_code=status.HTTP_201_CREATED)
async def create_dashboard(payload: DashboardCreate, db: AsyncSession = Depends(get_db)):
    try:
        svc = DashboardService(db)
        dashboard = await svc.create_dashboard(payload)
        return DashboardRead.model_validate(dashboard)
    except AppError as exc:
        raise _http(exc)


@router.post("/generate", response_model=DashboardRead, status_code=status.HTTP_201_CREATED)
async def generate_dashboard_from_nlp(
    payload: NLPDashboardRequest,
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate a dashboard from a natural-language prompt."""
    try:
        svc = DashboardService(db)
        dashboard = await svc.generate_from_nlp(
            prompt=payload.prompt,
            dataset_id=payload.dataset_id,
            dashboard_name=payload.dashboard_name,
        )
        return DashboardRead.model_validate(dashboard)
    except AppError as exc:
        raise _http(exc)


@router.get("/{dashboard_id}", response_model=DashboardRead)
async def get_dashboard(dashboard_id: str, db: AsyncSession = Depends(get_db)):
    try:
        svc = DashboardService(db)
        dashboard = await svc.get_dashboard(dashboard_id)
        return DashboardRead.model_validate(dashboard)
    except AppError as exc:
        raise _http(exc)


@router.put("/{dashboard_id}", response_model=DashboardRead)
async def update_dashboard(
    dashboard_id: str,
    payload: DashboardUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        svc = DashboardService(db)
        dashboard = await svc.update_dashboard(dashboard_id, payload)
        return DashboardRead.model_validate(dashboard)
    except AppError as exc:
        raise _http(exc)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(dashboard_id: str, db: AsyncSession = Depends(get_db)):
    try:
        svc = DashboardService(db)
        await svc.delete_dashboard(dashboard_id)
    except AppError as exc:
        raise _http(exc)


# ── Widget CRUD ───────────────────────────────────────────────────────────────

@router.post("/{dashboard_id}/widgets", response_model=WidgetRead, status_code=status.HTTP_201_CREATED)
async def add_widget(
    dashboard_id: str,
    payload: WidgetCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        svc = DashboardService(db)
        widget = await svc.add_widget(dashboard_id, payload)
        return WidgetRead.model_validate(widget)
    except AppError as exc:
        raise _http(exc)


@router.put("/{dashboard_id}/widgets/{widget_id}", response_model=WidgetRead)
async def update_widget(
    dashboard_id: str,
    widget_id: str,
    payload: WidgetUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        svc = DashboardService(db)
        widget = await svc.update_widget(widget_id, payload)
        return WidgetRead.model_validate(widget)
    except AppError as exc:
        raise _http(exc)


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    dashboard_id: str,
    widget_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        svc = DashboardService(db)
        await svc.delete_widget(widget_id)
    except AppError as exc:
        raise _http(exc)


@router.post("/{dashboard_id}/widgets/{widget_id}/data")
async def get_widget_data(
    dashboard_id: str,
    widget_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Execute the widget's SQL query and return the result rows."""
    from sqlalchemy import select
    from app.models.dashboard import Widget
    from app.core.exceptions import DashboardNotFound

    result = await db.execute(select(Widget).where(Widget.id == widget_id))
    widget = result.scalar_one_or_none()
    if not widget or widget.dashboard_id != dashboard_id:
        raise HTTPException(status_code=404, detail={"error": "Widget not found.", "code": "WIDGET_NOT_FOUND"})

    try:
        rows = await execute_dataset_query(widget.sql_query)
        return {
            "widget_id": widget_id,
            "chart_type": widget.chart_type,
            "title": widget.title,
            "data": rows,
            "row_count": len(rows),
        }
    except Exception as exc:
        logger.warning("widget_query_failed", widget_id=widget_id, error=str(exc))
        raise HTTPException(
            status_code=422,
            detail={"error": "Widget query failed.", "detail": str(exc), "code": "WIDGET_QUERY_ERROR"},
        )

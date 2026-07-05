"""
Dashboard Service — CRUD for dashboards/widgets plus NLP-driven auto-generation.
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DashboardNotFound, DatasetNotFound, NLPParseError
from app.core.security import validate_sql
from app.models.dashboard import Dashboard, Widget
from app.models.dataset import Dataset, DatasetColumn
from app.schemas.dashboard import DashboardCreate, DashboardUpdate, WidgetCreate, WidgetUpdate


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Dashboard CRUD ────────────────────────────────────────────────────────

    async def create_dashboard(self, payload: DashboardCreate) -> Dashboard:
        dashboard = Dashboard(
            name=payload.name,
            description=payload.description,
            dataset_id=payload.dataset_id,
        )
        self.db.add(dashboard)
        await self.db.flush()

        for w in payload.widgets:
            await self._add_widget(dashboard.id, w)

        await self.db.flush()
        logger.info("dashboard_created", dashboard_id=dashboard.id, name=payload.name)
        return dashboard

    async def list_dashboards(self) -> list[Dashboard]:
        result = await self.db.execute(select(Dashboard).order_by(Dashboard.created_at.desc()))
        return list(result.scalars().all())

    async def get_dashboard(self, dashboard_id: str) -> Dashboard:
        result = await self.db.execute(
            select(Dashboard).where(Dashboard.id == dashboard_id)
        )
        dashboard = result.scalar_one_or_none()
        if not dashboard:
            raise DashboardNotFound(dashboard_id)
        return dashboard

    async def update_dashboard(self, dashboard_id: str, payload: DashboardUpdate) -> Dashboard:
        dashboard = await self.get_dashboard(dashboard_id)
        if payload.name is not None:
            dashboard.name = payload.name
        if payload.description is not None:
            dashboard.description = payload.description
        await self.db.flush()
        return dashboard

    async def delete_dashboard(self, dashboard_id: str) -> None:
        dashboard = await self.get_dashboard(dashboard_id)
        await self.db.delete(dashboard)
        await self.db.flush()
        logger.info("dashboard_deleted", dashboard_id=dashboard_id)

    # ── Widget CRUD ───────────────────────────────────────────────────────────

    async def _add_widget(self, dashboard_id: str, payload: WidgetCreate) -> Widget:
        # Validate SQL before storing
        validated_sql = validate_sql(payload.sql_query)
        widget = Widget(
            dashboard_id=dashboard_id,
            dataset_id=payload.dataset_id,
            title=payload.title,
            chart_type=payload.chart_type,
            sql_query=validated_sql,
            config=payload.config,
            grid_x=payload.grid_x,
            grid_y=payload.grid_y,
            grid_w=payload.grid_w,
            grid_h=payload.grid_h,
            nlp_prompt=payload.nlp_prompt,
        )
        self.db.add(widget)
        return widget

    async def add_widget(self, dashboard_id: str, payload: WidgetCreate) -> Widget:
        await self.get_dashboard(dashboard_id)  # ensure it exists
        widget = await self._add_widget(dashboard_id, payload)
        await self.db.flush()
        logger.info("widget_added", dashboard_id=dashboard_id, widget_id=widget.id)
        return widget

    async def update_widget(self, widget_id: str, payload: WidgetUpdate) -> Widget:
        result = await self.db.execute(select(Widget).where(Widget.id == widget_id))
        widget = result.scalar_one_or_none()
        if not widget:
            raise DashboardNotFound(widget_id)

        if payload.title is not None:
            widget.title = payload.title
        if payload.chart_type is not None:
            widget.chart_type = payload.chart_type
        if payload.sql_query is not None:
            widget.sql_query = validate_sql(payload.sql_query)
        if payload.config is not None:
            widget.config = payload.config
        if payload.grid_x is not None:
            widget.grid_x = payload.grid_x
        if payload.grid_y is not None:
            widget.grid_y = payload.grid_y
        if payload.grid_w is not None:
            widget.grid_w = payload.grid_w
        if payload.grid_h is not None:
            widget.grid_h = payload.grid_h

        await self.db.flush()
        return widget

    async def delete_widget(self, widget_id: str) -> None:
        result = await self.db.execute(select(Widget).where(Widget.id == widget_id))
        widget = result.scalar_one_or_none()
        if not widget:
            raise DashboardNotFound(widget_id)
        await self.db.delete(widget)
        await self.db.flush()

    # ── NLP dashboard generation ──────────────────────────────────────────────

    async def generate_from_nlp(
        self,
        prompt: str,
        dataset_id: str,
        dashboard_name: str | None = None,
    ) -> Dashboard:
        """
        Auto-create a dashboard from a natural-language prompt.
        Detects requested chart types, generates queries, and lays out 3-6 widgets.
        """
        # Load dataset + schema
        ds_result = await self.db.execute(select(Dataset).where(Dataset.id == dataset_id))
        dataset = ds_result.scalar_one_or_none()
        if not dataset:
            raise DatasetNotFound(dataset_id)

        col_result = await self.db.execute(
            select(DatasetColumn).where(DatasetColumn.dataset_id == dataset_id)
        )
        columns = list(col_result.scalars().all())
        if not columns:
            raise NLPParseError(
                "Dataset has no column metadata.",
                "Run ingestion first.",
            )

        col_map = {c.column_name: c for c in columns}
        numeric_cols = [c.column_name for c in columns if c.detected_type == "numeric"]
        cat_cols = [c.column_name for c in columns if c.detected_type == "categorical"]
        date_cols = [c.column_name for c in columns if c.detected_type == "datetime"]
        table = dataset.table_name

        widgets_spec = _parse_dashboard_prompt(prompt, numeric_cols, cat_cols, date_cols)
        if not widgets_spec:
            # Fallback: standard overview
            widgets_spec = _default_widget_specs(numeric_cols, cat_cols, date_cols)

        # Ensure 3–6 widgets
        widgets_spec = widgets_spec[:6]
        while len(widgets_spec) < 3:
            widgets_spec.extend(_default_widget_specs(numeric_cols, cat_cols, date_cols)[:1])

        name = dashboard_name or f"Dashboard: {prompt[:50]}"
        dashboard = Dashboard(name=name, description=prompt, dataset_id=dataset_id)
        self.db.add(dashboard)
        await self.db.flush()

        grid_positions = _compute_grid(len(widgets_spec))

        for i, spec in enumerate(widgets_spec):
            sql = _build_widget_sql(spec, table, col_map)
            if not sql:
                continue
            try:
                validated_sql = validate_sql(sql)
            except Exception:
                continue

            gp = grid_positions[i]
            widget = Widget(
                dashboard_id=dashboard.id,
                dataset_id=dataset_id,
                title=spec["title"],
                chart_type=spec["chart_type"],
                sql_query=validated_sql,
                config=spec.get("config", {}),
                grid_x=gp["x"],
                grid_y=gp["y"],
                grid_w=gp["w"],
                grid_h=gp["h"],
                nlp_prompt=prompt,
            )
            self.db.add(widget)

        await self.db.flush()
        logger.info(
            "nlp_dashboard_generated",
            dashboard_id=dashboard.id,
            prompt=prompt[:80],
        )
        return dashboard


# ── Helper functions ──────────────────────────────────────────────────────────

_CHART_KEYWORDS: list[tuple[str, list[str]]] = [
    ("bar", ["bar chart", "bar graph", "bar plot", "grouped bar"]),
    ("line", ["line chart", "line graph", "trend", "over time", "time series"]),
    ("pie", ["pie chart", "pie graph", "donut", "proportion", "share"]),
    ("scatter", ["scatter plot", "scatter chart", "correlation", "scatter"]),
    ("histogram", ["histogram", "distribution", "frequency", "spread"]),
    ("table", ["table", "list", "show me", "display", "top", "bottom"]),
    ("metric", ["total", "count", "sum", "kpi", "metric", "number", "how many"]),
]


def _parse_dashboard_prompt(
    prompt: str,
    numeric_cols: list[str],
    cat_cols: list[str],
    date_cols: list[str],
) -> list[dict[str, Any]]:
    """Detect requested widget types and auto-assign columns."""
    lower = prompt.lower()
    specs: list[dict[str, Any]] = []

    for chart_type, keywords in _CHART_KEYWORDS:
        if any(kw in lower for kw in keywords):
            spec = _make_spec(chart_type, numeric_cols, cat_cols, date_cols)
            if spec:
                specs.append(spec)

    return specs


def _make_spec(
    chart_type: str,
    numeric_cols: list[str],
    cat_cols: list[str],
    date_cols: list[str],
) -> dict[str, Any] | None:
    nc = numeric_cols[0] if numeric_cols else None
    cc = cat_cols[0] if cat_cols else None
    dc = date_cols[0] if date_cols else None

    if chart_type == "line" and dc and nc:
        return {
            "chart_type": "line",
            "title": f"{nc} over time",
            "date_col": dc,
            "value_col": nc,
            "kind": "trend",
        }
    if chart_type in ("bar", "pie") and cc and nc:
        return {
            "chart_type": chart_type,
            "title": f"{nc} by {cc}",
            "group_col": cc,
            "value_col": nc,
            "kind": "aggregate",
        }
    if chart_type == "histogram" and nc:
        return {
            "chart_type": "histogram",
            "title": f"Distribution of {nc}",
            "value_col": nc,
            "kind": "distribution",
        }
    if chart_type == "scatter" and len(numeric_cols) >= 2:
        return {
            "chart_type": "scatter",
            "title": f"{numeric_cols[0]} vs {numeric_cols[1]}",
            "x_col": numeric_cols[0],
            "y_col": numeric_cols[1],
            "kind": "scatter",
        }
    if chart_type == "metric" and nc:
        return {
            "chart_type": "metric",
            "title": f"Total {nc}",
            "value_col": nc,
            "kind": "metric",
        }
    if chart_type == "table":
        return {
            "chart_type": "table",
            "title": "Data Overview",
            "kind": "table",
        }
    return None


def _default_widget_specs(
    numeric_cols: list[str],
    cat_cols: list[str],
    date_cols: list[str],
) -> list[dict[str, Any]]:
    specs = []
    nc = numeric_cols[0] if numeric_cols else None
    cc = cat_cols[0] if cat_cols else None
    dc = date_cols[0] if date_cols else None

    if nc:
        specs.append({"chart_type": "metric", "title": f"Total {nc}", "value_col": nc, "kind": "metric"})
    if cc and nc:
        specs.append({"chart_type": "bar", "title": f"{nc} by {cc}", "group_col": cc, "value_col": nc, "kind": "aggregate"})
    if dc and nc:
        specs.append({"chart_type": "line", "title": f"{nc} over time", "date_col": dc, "value_col": nc, "kind": "trend"})
    if nc:
        specs.append({"chart_type": "histogram", "title": f"Distribution of {nc}", "value_col": nc, "kind": "distribution"})
    specs.append({"chart_type": "table", "title": "Data Overview", "kind": "table"})

    return specs


def _build_widget_sql(
    spec: dict[str, Any],
    table: str,
    col_map: dict[str, Any],
) -> str | None:
    kind = spec.get("kind", "table")
    t = f'"{table}"'

    if kind == "metric":
        vc = spec.get("value_col")
        if vc and vc in col_map:
            return f'SELECT SUM("{vc}") AS total, AVG("{vc}") AS avg, COUNT(*) AS count FROM {t}'
        return f"SELECT COUNT(*) AS total FROM {t}"

    if kind == "aggregate":
        gc = spec.get("group_col")
        vc = spec.get("value_col")
        if gc and vc and gc in col_map and vc in col_map:
            return (
                f'SELECT "{gc}", SUM("{vc}") AS total '
                f"FROM {t} GROUP BY \"{gc}\" ORDER BY total DESC LIMIT 20"
            )

    if kind == "trend":
        dc = spec.get("date_col")
        vc = spec.get("value_col")
        if dc and vc and dc in col_map and vc in col_map:
            return (
                f"SELECT strftime('%Y-%m', \"{dc}\") AS period, "
                f'SUM("{vc}") AS total FROM {t} '
                f"WHERE \"{dc}\" IS NOT NULL GROUP BY period ORDER BY period"
            )

    if kind == "distribution":
        vc = spec.get("value_col")
        if vc and vc in col_map:
            return (
                f'SELECT "{vc}" AS value, COUNT(*) AS frequency '
                f"FROM {t} WHERE \"{vc}\" IS NOT NULL "
                f"GROUP BY \"{vc}\" ORDER BY frequency DESC LIMIT 50"
            )

    if kind == "scatter":
        xc = spec.get("x_col")
        yc = spec.get("y_col")
        if xc and yc and xc in col_map and yc in col_map:
            return f'SELECT "{xc}", "{yc}" FROM {t} WHERE "{xc}" IS NOT NULL AND "{yc}" IS NOT NULL LIMIT 1000'

    # Default: sample table
    return f"SELECT * FROM {t} LIMIT 100"


def _compute_grid(n: int) -> list[dict[str, int]]:
    """Assign grid positions for n widgets in a 12-column grid."""
    positions = []
    row = 0
    for i in range(n):
        col = (i % 2) * 6
        if i % 2 == 0 and i > 0:
            row += 4
        positions.append({"x": col, "y": row, "w": 6, "h": 4})
    return positions

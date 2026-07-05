"""Report generation: CSV, Excel (openpyxl), and PDF (reportlab)."""
from __future__ import annotations

import csv
import io

from sqlalchemy import select
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from sqlalchemy.orm import Session

from app.models import Campaign
from app.services import analytics_service

_COLUMNS = [
    ("campaign_name", "Campaign"),
    ("channel", "Channel"),
    ("sent", "Sent"),
    ("delivered", "Delivered"),
    ("opened", "Opened"),
    ("clicked", "Clicked"),
    ("bounced", "Bounced"),
    ("failed", "Failed"),
    ("open_rate", "Open Rate"),
    ("click_rate", "Click Rate"),
]


def _rows(db: Session) -> list[dict]:
    campaigns = list(db.scalars(select(Campaign)))
    return [analytics_service.campaign_metrics(db, c) for c in campaigns]


def to_csv(db: Session) -> bytes:
    rows = _rows(db)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([label for _, label in _COLUMNS])
    for r in rows:
        writer.writerow([r.get(key, "") for key, _ in _COLUMNS])
    return buf.getvalue().encode("utf-8")


def to_excel(db: Session) -> bytes:
    rows = _rows(db)
    wb = Workbook()
    ws = wb.active
    ws.title = "Campaign Performance"
    ws.append([label for _, label in _COLUMNS])
    for r in rows:
        ws.append([r.get(key, "") for key, _ in _COLUMNS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf(db: Session) -> bytes:
    rows = _rows(db)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Campaign Performance Report")
    header = [label for _, label in _COLUMNS]
    data = [header] + [[str(r.get(key, "")) for key, _ in _COLUMNS] for r in rows]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976d2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ]
        )
    )
    doc.build([table])
    return buf.getvalue()


def generate(db: Session, fmt: str) -> tuple[bytes, str, str]:
    """Return (content, media_type, filename)."""
    if fmt == "excel":
        return (
            to_excel(db),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "campaign_report.xlsx",
        )
    if fmt == "pdf":
        return to_pdf(db), "application/pdf", "campaign_report.pdf"
    return to_csv(db), "text/csv", "campaign_report.csv"

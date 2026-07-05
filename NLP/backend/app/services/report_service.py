"""
Report Service — CRUD for reports, section management,
CSV export, and PDF export via ReportLab.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatasetNotFound, ProcessingError, ReportNotFound
from app.database import execute_dataset_query
from app.models.dataset import Dataset
from app.models.report import Report, ReportSection
from app.schemas.report import ReportCreate, ReportSectionCreate


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create_report(self, payload: ReportCreate) -> Report:
        # Verify dataset exists
        ds = await self.db.get(Dataset, payload.dataset_id)
        if not ds:
            raise DatasetNotFound(payload.dataset_id)

        report = Report(
            dataset_id=payload.dataset_id,
            title=payload.title,
            description=payload.description,
            status="draft",
        )
        self.db.add(report)
        await self.db.flush()

        for i, sec in enumerate(payload.sections):
            section = ReportSection(
                report_id=report.id,
                order_index=sec.order_index if sec.order_index is not None else i,
                section_type=sec.section_type,
                title=sec.title,
                content=sec.content,
                sql_query=sec.sql_query,
            )
            self.db.add(section)

        await self.db.flush()
        logger.info("report_created", report_id=report.id, dataset_id=payload.dataset_id)
        return report

    async def list_reports(self, dataset_id: str | None = None) -> list[Report]:
        q = select(Report).order_by(Report.created_at.desc())
        if dataset_id:
            q = q.where(Report.dataset_id == dataset_id)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_report(self, report_id: str) -> Report:
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if not report:
            raise ReportNotFound(report_id)
        return report

    async def delete_report(self, report_id: str) -> None:
        report = await self.get_report(report_id)
        await self.db.delete(report)
        await self.db.flush()
        logger.info("report_deleted", report_id=report_id)

    async def add_section(self, report_id: str, payload: ReportSectionCreate) -> ReportSection:
        await self.get_report(report_id)
        section = ReportSection(
            report_id=report_id,
            order_index=payload.order_index,
            section_type=payload.section_type,
            title=payload.title,
            content=payload.content,
            sql_query=payload.sql_query,
        )
        self.db.add(section)
        await self.db.flush()
        return section

    # ── Report generation ─────────────────────────────────────────────────────

    async def generate_report(self, report_id: str) -> Report:
        """
        Populate section content by executing each section's sql_query
        and storing the result rows in section.content.
        """
        report = await self.get_report(report_id)
        report.status = "generating"
        await self.db.flush()

        try:
            for section in report.sections:
                if section.sql_query:
                    rows = await execute_dataset_query(section.sql_query)
                    section.content = {"rows": rows[:500]}

            report.status = "ready"
        except Exception as exc:
            logger.exception("report_generation_failed", report_id=report_id, error=str(exc))
            report.status = "error"
            report.error_message = str(exc)[:1000]

        await self.db.flush()
        return report

    # ── CSV Export ────────────────────────────────────────────────────────────

    async def export_csv(self, report_id: str) -> bytes:
        """Return the report data as CSV bytes."""
        report = await self.get_report(report_id)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([f"Report: {report.title}"])
        writer.writerow([f"Dataset ID: {report.dataset_id}"])
        writer.writerow([f"Generated: {datetime.utcnow().isoformat()}"])
        writer.writerow([])

        for section in report.sections:
            writer.writerow([f"=== {section.title} ==="])

            content = section.content or {}
            rows = content.get("rows", [])

            if rows:
                # Header row
                writer.writerow(list(rows[0].keys()))
                for row in rows:
                    writer.writerow([str(v) if v is not None else "" for v in row.values()])
            else:
                writer.writerow(["No data available."])

            writer.writerow([])

        return output.getvalue().encode("utf-8-sig")

    # ── PDF Export ────────────────────────────────────────────────────────────

    async def export_pdf(self, report_id: str) -> bytes:
        """Build a PDF from the report using ReportLab."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        report = await self.get_report(report_id)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=report.title,
            author="NLP Data Intelligence Platform",
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=20,
            spaceAfter=12,
            textColor=colors.HexColor("#1a1a2e"),
            alignment=TA_CENTER,
        )
        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=14,
            spaceAfter=6,
            textColor=colors.HexColor("#16213e"),
        )
        normal_style = styles["Normal"]

        story = []

        # ── Cover ──────────────────────────────────────────────────────────
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(report.title, title_style))
        story.append(
            Paragraph(
                f"Dataset ID: {report.dataset_id}  |  "
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                normal_style,
            )
        )
        if report.description:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(report.description, normal_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
        story.append(Spacer(1, 0.5 * cm))

        # ── Sections ───────────────────────────────────────────────────────
        for section in report.sections:
            story.append(Paragraph(section.title, section_style))

            content = section.content or {}
            rows = content.get("rows", [])

            if rows:
                # Build table
                headers = list(rows[0].keys())
                table_data = [headers]
                for row in rows[:50]:  # cap at 50 rows per section in PDF
                    table_data.append(
                        [str(row.get(h, ""))[:60] for h in headers]
                    )

                col_width = (A4[0] - 4 * cm) / max(len(headers), 1)
                t = Table(table_data, colWidths=[col_width] * len(headers), repeatRows=1)
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 9),
                            ("FONTSIZE", (0, 1), (-1, -1), 8),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("TOPPADDING", (0, 0), (-1, -1), 4),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                story.append(t)
                if len(rows) > 50:
                    story.append(
                        Paragraph(
                            f"... and {len(rows) - 50} more rows (truncated in PDF).",
                            normal_style,
                        )
                    )
            else:
                story.append(Paragraph("No data available for this section.", normal_style))

            story.append(Spacer(1, 0.4 * cm))

        # ── Footer ─────────────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
        story.append(
            Paragraph(
                "Generated by NLP Data Intelligence Platform",
                ParagraphStyle("Footer", parent=normal_style, fontSize=8, textColor=colors.grey),
            )
        )

        doc.build(story)
        return buffer.getvalue()

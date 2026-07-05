"""
ORM models for reports and their sections.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dataset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status: draft | generating | ready | error
    status: Mapped[str] = mapped_column(String(20), default="draft")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sections: Mapped[list[ReportSection]] = relationship(
        "ReportSection",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ReportSection.order_index",
    )


class ReportSection(Base):
    __tablename__ = "report_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    section_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # summary | table | chart | text | stats

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # SQL query whose results populate this section (if data-driven)
    sql_query: Mapped[str | None] = mapped_column(Text, nullable=True)

    report: Mapped[Report] = relationship("Report", back_populates="sections")

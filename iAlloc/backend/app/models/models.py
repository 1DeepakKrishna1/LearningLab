"""SQLAlchemy ORM models for the iAlloc generalized platform."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class UserRole(str, enum.Enum):
    product_admin = "product_admin"
    system_admin = "system_admin"
    applicant = "applicant"
    verifier = "verifier"
    evaluator = "evaluator"
    allocation_authority = "allocation_authority"
    payment_agency = "payment_agency"
    auditor = "auditor"
    support = "support"
    institution = "institution"
    reporting_authority = "reporting_authority"


# Roles that are scoped to a single system (everyone except the product admin).
SYSTEM_SCOPED_ROLES = [r for r in UserRole if r != UserRole.product_admin]
STAKEHOLDER_ROLES = [
    UserRole.applicant,
    UserRole.verifier,
    UserRole.evaluator,
    UserRole.allocation_authority,
    UserRole.payment_agency,
    UserRole.auditor,
    UserRole.support,
    UserRole.institution,
    UserRole.reporting_authority,
]


class SystemDomain(str, enum.Enum):
    examination = "examination"
    university_admission = "university_admission"
    recruitment = "recruitment"
    scholarship = "scholarship"
    housing = "housing"
    govt_benefit = "govt_benefit"
    tender = "tender"
    generic = "generic"


class SystemStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    closed = "closed"


class ApplicationStatus(str, enum.Enum):
    draft = "draft"
    in_progress = "in_progress"
    eligible = "eligible"
    ineligible = "ineligible"
    evaluated = "evaluated"
    ranked = "ranked"
    allocated = "allocated"
    enrolled = "enrolled"
    rejected = "rejected"
    withdrawn = "withdrawn"


class StageStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"


class DocStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


# --------------------------------------------------------------------------- #
# Core tables
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    system_id: Mapped[int | None] = mapped_column(
        ForeignKey("systems.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    system: Mapped["System | None"] = relationship(
        back_populates="members", foreign_keys=[system_id]
    )


class System(Base):
    """A configured instance of the canonical lifecycle (one per domain deployment)."""

    __tablename__ = "systems"
    __table_args__ = (UniqueConstraint("key", name="uq_systems_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[SystemDomain] = mapped_column(Enum(SystemDomain), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[SystemStatus] = mapped_column(
        Enum(SystemStatus), default=SystemStatus.draft
    )
    # JSON configuration: stages, form_fields, ranking, allocation settings.
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    members: Mapped[list["User"]] = relationship(
        back_populates="system", foreign_keys="User.system_id"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="system", cascade="all, delete-orphan"
    )
    options: Mapped[list["AllocationOption"]] = relationship(
        back_populates="system", cascade="all, delete-orphan"
    )


class AllocationOption(Base):
    """A finite resource being allocated: seat / fund / room / job / contract."""

    __tablename__ = "allocation_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(
        ForeignKey("systems.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    filled: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    system: Mapped["System"] = relationship(back_populates="options")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int] = mapped_column(
        ForeignKey("systems.id", ondelete="CASCADE"), nullable=False
    )
    applicant_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reference_no: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    current_stage_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.draft
    )
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # form field values
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    system: Mapped["System"] = relationship(back_populates="applications")
    applicant: Mapped["User"] = relationship(foreign_keys=[applicant_id])
    stage_records: Mapped[list["StageRecord"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    preferences: Mapped[list["Preference"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    allocations: Mapped[list["Allocation"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class StageRecord(Base):
    """Progress of one application through one configured stage."""

    __tablename__ = "stage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    stage_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus), default=StageStatus.pending
    )
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    remarks: Mapped[str] = mapped_column(Text, default="")
    completed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    application: Mapped["Application"] = relationship(back_populates="stage_records")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(64), default="other")
    file_ref: Mapped[str] = mapped_column(String(512), default="")
    content_text: Mapped[str] = mapped_column(Text, default="")  # extracted/typed text
    status: Mapped[DocStatus] = mapped_column(Enum(DocStatus), default=DocStatus.pending)
    verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    remarks: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    application: Mapped["Application"] = relationship(back_populates="documents")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    stage_key: Mapped[str] = mapped_column(String(64), default="evaluation")
    evaluator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)
    max_score: Mapped[float] = mapped_column(Float, default=100.0)
    criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    remarks: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    application: Mapped["Application"] = relationship(back_populates="evaluations")


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    option_key: Mapped[str] = mapped_column(String(64), nullable=False)
    option_label: Mapped[str] = mapped_column(String(255), default="")
    priority: Mapped[int] = mapped_column(Integer, default=1)

    application: Mapped["Application"] = relationship(back_populates="preferences")


class Allocation(Base):
    __tablename__ = "allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    option_key: Mapped[str] = mapped_column(String(64), nullable=False)
    option_label: Mapped[str] = mapped_column(String(255), default="")
    round: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="allotted")  # allotted/accepted/declined
    allocated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    application: Mapped["Application"] = relationship(back_populates="allocations")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    purpose: Mapped[str] = mapped_column(String(128), default="application_fee")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.pending
    )
    reference: Mapped[str] = mapped_column(String(64), default="")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    application: Mapped["Application"] = relationship(back_populates="payments")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int | None] = mapped_column(
        ForeignKey("systems.id", ondelete="SET NULL"), nullable=True
    )
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class AIInvocation(Base):
    __tablename__ = "ai_invocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id: Mapped[int | None] = mapped_column(
        ForeignKey("systems.id", ondelete="SET NULL"), nullable=True
    )
    stage_key: Mapped[str] = mapped_column(String(64), default="")
    task: Mapped[str] = mapped_column(String(64), default="")
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(128), default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    response: Mapped[str] = mapped_column(Text, default="")
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

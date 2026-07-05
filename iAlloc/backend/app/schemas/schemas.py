from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    ApplicationStatus,
    DocStatus,
    PaymentStatus,
    StageStatus,
    SystemDomain,
    SystemStatus,
    UserRole,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# --------------------------- Auth / Users --------------------------- #
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    system_id: int | None = None
    is_active: bool


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=6)
    role: UserRole
    system_id: int | None = None


class SelfRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(min_length=6)
    system_id: int
    role: UserRole = UserRole.applicant


# --------------------------- Systems --------------------------- #
class SystemCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_\-]+$", max_length=64)
    name: str
    domain: SystemDomain
    description: str = ""
    system_admin_email: EmailStr | None = None
    system_admin_name: str | None = None
    system_admin_password: str | None = None


class SystemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: SystemStatus | None = None
    config: dict | None = None


class SystemOut(ORMModel):
    id: int
    key: str
    name: str
    domain: SystemDomain
    description: str
    status: SystemStatus
    config: dict
    created_at: datetime


class SystemSummary(ORMModel):
    id: int
    key: str
    name: str
    domain: SystemDomain
    status: SystemStatus


class DomainTemplate(BaseModel):
    domain: str
    name_suggestion: str


# --------------------------- Stage config --------------------------- #
class StageAIConfig(BaseModel):
    enabled: bool = False
    task: str = ""
    model: str | None = None
    instructions: str = ""


class StageConfigUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    roles: list[str] | None = None
    ai: StageAIConfig | None = None


# --------------------------- Allocation options --------------------------- #
class OptionCreate(BaseModel):
    key: str
    label: str
    capacity: int = 0
    meta: dict = {}


class OptionOut(ORMModel):
    id: int
    key: str
    label: str
    capacity: int
    filled: int
    meta: dict


# --------------------------- Applications --------------------------- #
class ApplicationCreate(BaseModel):
    data: dict[str, Any] = {}


class ApplicationUpdate(BaseModel):
    data: dict[str, Any]


class StageProgress(BaseModel):
    key: str
    name: str
    type: str
    order: int
    ai_enabled: bool
    status: str
    is_current: bool
    remarks: str = ""


class ApplicationOut(ORMModel):
    id: int
    system_id: int
    applicant_id: int
    reference_no: str
    current_stage_key: str | None
    status: ApplicationStatus
    data: dict
    score: float | None
    rank: int | None
    created_at: datetime


class ApplicationDetail(ApplicationOut):
    progress: list[StageProgress] = []
    applicant_name: str | None = None


class StageActionRequest(BaseModel):
    stage_key: str
    data: dict[str, Any] = {}
    remarks: str = ""
    status: StageStatus = StageStatus.completed


# --------------------------- Documents --------------------------- #
class DocumentCreate(BaseModel):
    name: str
    doc_type: str = "other"
    content_text: str = ""
    file_ref: str = ""


class DocumentVerify(BaseModel):
    status: DocStatus
    remarks: str = ""


class DocumentOut(ORMModel):
    id: int
    application_id: int
    name: str
    doc_type: str
    status: DocStatus
    content_text: str
    remarks: str
    uploaded_at: datetime


# --------------------------- Evaluation --------------------------- #
class EvaluationCreate(BaseModel):
    application_id: int
    stage_key: str = "evaluation"
    score: float
    max_score: float = 100.0
    criteria: dict = {}
    remarks: str = ""


class EvaluationOut(ORMModel):
    id: int
    application_id: int
    stage_key: str
    score: float
    max_score: float
    criteria: dict
    remarks: str
    created_at: datetime


# --------------------------- Preference --------------------------- #
class PreferenceItem(BaseModel):
    option_key: str
    option_label: str = ""
    priority: int


class PreferenceSet(BaseModel):
    preferences: list[PreferenceItem]


class PreferenceOut(ORMModel):
    id: int
    option_key: str
    option_label: str
    priority: int


# --------------------------- Allocation --------------------------- #
class AllocationOut(ORMModel):
    id: int
    application_id: int
    option_key: str
    option_label: str
    round: int
    status: str
    created_at: datetime


class AllocationDecision(BaseModel):
    decision: str  # accepted / declined


# --------------------------- Payment --------------------------- #
class PaymentCreate(BaseModel):
    amount: float
    currency: str = "INR"
    purpose: str = "application_fee"


class PaymentOut(ORMModel):
    id: int
    application_id: int
    amount: float
    currency: str
    purpose: str
    status: PaymentStatus
    reference: str
    created_at: datetime


# --------------------------- AI --------------------------- #
class AIRequest(BaseModel):
    system_id: int
    stage_key: str
    user_input: str = ""
    application_id: int | None = None
    task: str | None = None  # optional override among the stage's available tasks


class AIResponse(BaseModel):
    task: str
    model: str
    content: str
    tokens: int


# --------------------------- Audit / Reports --------------------------- #
class AuditOut(ORMModel):
    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    detail: dict
    created_at: datetime


class SystemReport(BaseModel):
    system_id: int
    total_applications: int
    by_status: dict[str, int]
    options: list[OptionOut]
    fill_rate: float


Token.model_rebuild()

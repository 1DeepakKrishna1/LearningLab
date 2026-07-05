from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import hashlib


def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


class AgentType(str, Enum):
    # Lifecycle sentinels
    START = "start"
    END = "end"
    # Core types
    AUTOMATIC = "automatic"
    ROLE_BASED = "role_based"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    HUMAN_REVIEW = "human_review"
    CONDITIONAL = "conditional"
    PARALLEL = "parallel"
    # Advanced AI agent patterns
    PROMPT_AGENT = "prompt_agent"
    REACT_AGENT = "react_agent"
    REFLECTION_AGENT = "reflection_agent"
    GUARDRAILS = "guardrails"
    ORCHESTRATOR = "orchestrator"
    SUPERVISOR = "supervisor"

    AI_AGENT = "ai_agent"


class ToolType(str, Enum):
    API_CALL = "api_call"
    DATA_TRANSFORM = "data_transform"
    NOTIFICATION = "notification"
    DATABASE = "database"
    FILE_OPERATION = "file_operation"
    AI_MODEL = "ai_model"
    WEB_SEARCH = "web_search"

    LEGAL_SEARCH = "legal_search"
    ANALYSIS = "analysis"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


# ── Triggers (Start agent) ────────────────────────────────
class TriggerType(str, Enum):
    MANUAL = "manual"
    WEBHOOK = "webhook"
    CRON = "cron"
    GOOGLE_SHEET = "google_sheet"
    EMAIL = "email"


class Trigger(BaseModel):
    """A single trigger attached to a Start agent. The `config` dict carries
    per-type fields (e.g. cron expression, sheet id, webhook secret)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TriggerType
    name: str = ""
    enabled: bool = True
    config: Dict[str, Any] = {}
    # Cron bookkeeping (server-managed):
    last_fired_at: Optional[datetime] = None


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ── Invoke parameters ─────────────────────────────────────

class InvokeParameterType(str, Enum):
    CONSTANT = "constant"
    WORKFLOW = "workflow"
    TOOL = "tool"
    DATA_MODEL = "data_model"


class InvokeParameter(BaseModel):
    name: str
    value_type: InvokeParameterType = InvokeParameterType.CONSTANT
    value: str = ""
    description: str = ""


class InvokeConfig(BaseModel):
    input_parameters: List[InvokeParameter] = []
    output_parameters: List[InvokeParameter] = []


# ── Tool ──────────────────────────────────────────────────
class Tool(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    type: ToolType
    properties: Dict[str, Any] = {}
    icon: str = "wrench"
    review_status: str = "approved"   # approved | pending | rejected


class ToolCreate(BaseModel):
    name: str
    description: str
    type: ToolType
    properties: Dict[str, Any] = {}


# ── Agent ─────────────────────────────────────────────────
class Agent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    type: AgentType
    tools: List[str] = []        # tool ids
    tool_configs: Dict[str, Dict[str, Any]] = {}  # tool_id → per-agent property overrides
    properties: Dict[str, Any] = {}
    icon: str = "bot"
    color: str = "#6366f1"
    review_status: str = "approved"   # approved | pending | rejected
    invoke: InvokeConfig = Field(default_factory=InvokeConfig)


class AgentCreate(BaseModel):
    name: str
    description: str
    type: AgentType
    tools: List[str] = []
    tool_configs: Dict[str, Dict[str, Any]] = {}
    properties: Dict[str, Any] = {}
    invoke: InvokeConfig = Field(default_factory=InvokeConfig)


# ── Workflow ──────────────────────────────────────────────
class NodePosition(BaseModel):
    x: float
    y: float


class WorkflowNode(BaseModel):
    id: str
    node_kind: str = "agent"          # "agent" | "tool"
    agent_id: Optional[str] = None
    tool_id: Optional[str] = None
    position: NodePosition
    data: Dict[str, Any] = {}


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    type: str = "smoothstep"


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    status: WorkflowStatus = WorkflowStatus.DRAFT
    nodes: List[WorkflowNode] = []
    edges: List[WorkflowEdge] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_template: bool = False
    tags: List[str] = []


class WorkflowCreate(BaseModel):
    name: str
    description: str
    status: WorkflowStatus = WorkflowStatus.DRAFT
    nodes: List[WorkflowNode] = []
    edges: List[WorkflowEdge] = []
    tags: List[str] = []


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[WorkflowStatus] = None
    nodes: Optional[List[WorkflowNode]] = None
    edges: Optional[List[WorkflowEdge]] = None
    tags: Optional[List[str]] = None


# ── Execution ─────────────────────────────────────────────
class StepResult(BaseModel):
    node_id: str
    agent_name: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    input: Dict[str, Any] = {}
    output: Dict[str, Any] = {}
    logs: List[str] = []
    duration_ms: Optional[int] = None
    node_kind: str = "agent"               # "agent" | "tool"
    # Human-in-the-loop / human-review fields
    requires_human_input: bool = False
    review_mode: Optional[str] = None      # "hitl" (active collaboration) | "review" (validation checkpoint)
    judgment_options: List[str] = []
    input_fields: Dict[str, Any] = {}      # field_name → default value
    human_response: Optional[Dict[str, Any]] = None  # filled in by frontend
    ai_output: Dict[str, Any] = {}         # AI-produced output the human collaborates on / validates
    download_files: List[Dict[str, Any]] = []  # files the human can download during run (name/type/size_kb/content)
    allow_upload: bool = False             # whether the form accepts file uploads (HITL)
    # Invoke parameter resolution
    invoke_inputs: Dict[str, Any] = {}     # resolved input parameter values
    invoke_outputs: Dict[str, Any] = {}    # resolved output parameter values


class ExecutionRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    steps: List[StepResult] = []
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    data_model_instance: Dict[str, Any] = {}  # runtime data model JSON state


# ── AI Chat ───────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    workflow_context: Optional[Dict[str, Any]] = None
    history: List[ChatMessage] = []


# ── Field / Entity types ──────────────────────────────────

class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    OBJECT = "object"
    ARRAY = "array"


class DataModelField(BaseModel):
    name: str
    field_type: FieldType = FieldType.STRING
    required: bool = False
    description: str = ""
    validation: Optional[str] = None
    default_value: Optional[Any] = None


class DataModelEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    fields: List[DataModelField] = []


class RelationType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class DataModelRelationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_entity: str   # entity id
    to_entity: str     # entity id
    relation_type: RelationType = RelationType.ONE_TO_MANY
    label: str = ""


class DataModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    entities: List[DataModelEntity] = []
    relationships: List[DataModelRelationship] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DataModelCreate(BaseModel):
    name: str
    description: str = ""
    entities: List[DataModelEntity] = []
    relationships: List[DataModelRelationship] = []


class DataModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    entities: Optional[List[DataModelEntity]] = None
    relationships: Optional[List[DataModelRelationship]] = None


class DataModelImport(BaseModel):
    json_schema: Dict[str, Any]


class DataModelAISuggest(BaseModel):
    workflow_name: str
    workflow_description: str


# ── Workflow Association ──────────────────────────────────

class Environment(str, Enum):
    DEV = "dev"
    UAT = "uat"
    PROD = "prod"


class InputMapping(BaseModel):
    source: str
    target: str
    description: str = ""


class ActivityBinding(BaseModel):
    node_id: str
    agent_name: str
    input_mappings: List[Dict[str, str]] = []
    output_mappings: List[Dict[str, str]] = []


class WorkflowAssociation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    data_model_id: Optional[str] = None
    project: str = ""
    environment: Environment = Environment.DEV
    global_context: Dict[str, Any] = {}
    input_mappings: List[InputMapping] = []
    default_values: Dict[str, Any] = {}
    validation_rules: List[Dict[str, Any]] = []
    activity_bindings: List[ActivityBinding] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowAssociationUpsert(BaseModel):
    workflow_id: str
    data_model_id: Optional[str] = None
    project: str = ""
    environment: Environment = Environment.DEV
    global_context: Dict[str, Any] = {}
    input_mappings: List[InputMapping] = []
    default_values: Dict[str, Any] = {}
    validation_rules: List[Dict[str, Any]] = []
    activity_bindings: List[ActivityBinding] = []


# ── Review / Publish ──────────────────────────────────────

class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str                   # "tool" | "agent" | "template"
    item_id: str
    item_name: str
    status: ReviewStatus = ReviewStatus.PENDING
    submitted_by_id: str
    submitted_by_name: str
    reviewed_by_id: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    item_data: Dict[str, Any] = {}


class ReviewCreate(BaseModel):
    type: str
    item_id: str
    item_name: str
    item_data: Dict[str, Any] = {}


class ReviewDecision(BaseModel):
    notes: Optional[str] = None


# ── User / Auth ──────────────────────────────────────────

class UserRole(str, Enum):
    PRODUCT_ADMIN = "product_admin"
    PROCESS_ADMIN = "process_admin"
    ORG_USER = "org_user"
    CUST_USER = "cust_user"
    CUST_ADMIN = "cust_admin"


class UserInDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    password_hash: str
    role: UserRole
    group_ids: List[str] = []
    project_ids: List[str] = []
    is_active: bool = True
    avatar: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: UserRole
    group_ids: List[str] = []
    project_ids: List[str] = []
    is_active: bool = True
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: UserRole
    group_ids: List[str] = []
    project_ids: List[str] = []


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    group_ids: Optional[List[str]] = None
    project_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


# ── Groups ───────────────────────────────────────────────

class Group(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    user_ids: List[str] = []
    project_ids: List[str] = []
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GroupCreate(BaseModel):
    name: str
    description: str = ""
    user_ids: List[str] = []
    project_ids: List[str] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    user_ids: Optional[List[str]] = None
    project_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ── Projects ─────────────────────────────────────────────

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    launchurl: Optional[str] = None
    workflow_ids: List[str] = []
    user_ids: List[str] = []
    group_ids: List[str] = []
    owner_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    launchurl: Optional[str] = None
    workflow_ids: List[str] = []
    user_ids: List[str] = []
    group_ids: List[str] = []


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    launchurl: Optional[str] = None
    workflow_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    group_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ── Audit Log ────────────────────────────────────────────

class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_email: str
    user_name: str
    action: str           # create | update | delete | login | logout | execute | approve | reject
    resource_type: str    # user | group | project | workflow | tool | agent | template | data_model
    resource_id: str
    resource_name: str
    details: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None

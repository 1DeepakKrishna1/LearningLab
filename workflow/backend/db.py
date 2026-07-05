# Shared in-memory stores – imported by all route modules
from typing import Dict, Set, List
from models import Tool, Agent, Workflow, ExecutionRun, DataModel, WorkflowAssociation
from models import UserInDB, Group, Project, AuditLog, ReviewItem

tools_db: Dict[str, Tool] = {}
agents_db: Dict[str, Agent] = {}
workflows_db: Dict[str, Workflow] = {}
executions_db: Dict[str, ExecutionRun] = {}
library_workflow_ids: Set[str] = set()
data_models_db: Dict[str, DataModel] = {}
workflow_associations_db: Dict[str, WorkflowAssociation] = {}

# Auth / IAM stores
users_db: Dict[str, UserInDB] = {}          # id → UserInDB
sessions_db: Dict[str, str] = {}            # token → user_id
groups_db: Dict[str, Group] = {}
projects_db: Dict[str, Project] = {}

# Governance stores
audit_logs: List[AuditLog] = []
reviews_db: Dict[str, ReviewItem] = {}

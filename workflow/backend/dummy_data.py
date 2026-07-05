import json
import os

from models import Tool, Agent, Workflow, WorkflowNode, WorkflowEdge, NodePosition
from models import WorkflowStatus, UserInDB, Group, Project, _hash_password, UserRole
from db import tools_db, agents_db, workflows_db, library_workflow_ids
from db import users_db, groups_db, projects_db
from config import get_data_dir
import org_config

_DATA_FILE = get_data_dir() / os.getenv("MOCKDATA", "dummy_data.json")

with _DATA_FILE.open(encoding="utf-8") as _f:
    _data = json.load(_f)

DUMMY_TOOLS = _data["tools"]
DUMMY_AGENTS = _data["agents"]
TEMPLATE_WORKFLOWS = _data["templates"]


def _build_workflow(data: dict) -> Workflow:
    nodes = [
        WorkflowNode(
            id=n["id"],
            agent_id=n.get("agent_id"),
            position=NodePosition(**n["position"]),
            data=n.get("data", {}),
        )
        for n in data["nodes"]
    ]
    edges = [
        WorkflowEdge(id=e["id"], source=e["source"], target=e["target"], label=e.get("label"))
        for e in data["edges"]
    ]
    return Workflow(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        status=WorkflowStatus(data["status"]),
        nodes=nodes,
        edges=edges,
        is_template=data.get("is_template", False),
        tags=data.get("tags", []),
    )


def _seed_iam():
    """Seed default users, groups, and projects (only if not already loaded from disk)."""
    if users_db:
        return  # already loaded from persistence

    _domain = org_config.get_org_domain()

    # ── Default users ─────────────────────────────────────
    admin = UserInDB(
        id="user-admin-001",
        email=f"admin@{_domain}",
        name="Product Admin",
        password_hash=_hash_password("Admin@123"),
        role=UserRole.PRODUCT_ADMIN,
        is_active=True,
    )
    org_admin = UserInDB(
        id="user-orgadmin-001",
        email=f"orgadmin@{_domain}",
        name="Process Admin",
        password_hash=_hash_password("Admin@123"),
        role=UserRole.PROCESS_ADMIN,
        is_active=True,
    )
    process_admin = UserInDB(
        id="user-processadmin-001",
        email=f"processadmin@{_domain}",
        name="Process Admin",
        password_hash=_hash_password("Admin@123"),
        role=UserRole.PROCESS_ADMIN,
        is_active=True,
    )
    alice = UserInDB(
        id="user-alice-001",
        email=f"alice@{_domain}",
        name="Alice Johnson",
        password_hash=_hash_password("User@123"),
        role=UserRole.ORG_USER,
        is_active=True,
    )
    bob = UserInDB(
        id="user-bob-001",
        email=f"bob@{_domain}",
        name="Bob Smith",
        password_hash=_hash_password("User@123"),
        role=UserRole.ORG_USER,
        is_active=True,
    )
    carol = UserInDB(
        id="user-carol-001",
        email=f"carol@{_domain}",
        name="Carol Davis",
        password_hash=_hash_password("User@123"),
        role=UserRole.ORG_USER,
        is_active=True,
    )

    cust_user = UserInDB(
        id="user-custuser-001",
        email=f"custuser@{_domain}",
        name="Customer User",
        password_hash=_hash_password("User@123"),
        role=UserRole.CUST_USER,
        is_active=True,
    )
    cust_admin = UserInDB(
        id="user-custadmin-001",
        email=f"custadmin@{_domain}",
        name="Customer Admin",
        password_hash=_hash_password("Admin@123"),
        role=UserRole.CUST_ADMIN,
        is_active=True,
    )

    for u in [admin, org_admin, process_admin, alice, bob, carol, cust_user, cust_admin]:
        users_db[u.id] = u

    # ── Default groups ────────────────────────────────────
    grp_ops = Group(
        id="grp-operations",
        name="Operations Team",
        description="Handles loan and onboarding workflows",
        user_ids=[alice.id, bob.id],
    )
    grp_finance = Group(
        id="grp-finance",
        name="Finance Team",
        description="Manages insurance and purchase order workflows",
        user_ids=[carol.id],
    )
    grp_admins = Group(
        id="grp-admins",
        name="Administrators",
        description="Platform administrators",
        user_ids=[admin.id, org_admin.id],
    )

    for g in [grp_ops, grp_finance, grp_admins]:
        groups_db[g.id] = g

    alice.group_ids = [grp_ops.id]
    bob.group_ids = [grp_ops.id]
    carol.group_ids = [grp_finance.id]
    admin.group_ids = [grp_admins.id]
    org_admin.group_ids = [grp_admins.id]

    # ── Default projects ──────────────────────────────────
    # Collect template workflow IDs by name
    loan_ids = [wf.id for wf in workflows_db.values() if "loan" in wf.name.lower() or "sanction" in wf.name.lower()]
    kyc_ids = [wf.id for wf in workflows_db.values() if "kyc" in wf.name.lower() or "onboard" in wf.name.lower()]
    ins_ids = [wf.id for wf in workflows_db.values() if "insurance" in wf.name.lower() or "claim" in wf.name.lower()]
    po_ids = [wf.id for wf in workflows_db.values() if "purchase" in wf.name.lower() or "order" in wf.name.lower()]

    proj_loan = Project(
        id="proj-loan-001",
        name="Loan Operations",
        description="Loan sanction and credit processing workflows",
        workflow_ids=loan_ids,
        user_ids=[alice.id, bob.id, org_admin.id],
        group_ids=[grp_ops.id],
        owner_id=org_admin.id,
    )
    proj_kyc = Project(
        id="proj-kyc-001",
        name="Customer Onboarding",
        description="KYC and customer onboarding workflows",
        workflow_ids=kyc_ids,
        user_ids=[alice.id, org_admin.id],
        group_ids=[grp_ops.id],
        owner_id=org_admin.id,
    )
    proj_finance = Project(
        id="proj-finance-001",
        name="Finance & Insurance",
        description="Insurance claims and purchase order workflows",
        workflow_ids=ins_ids + po_ids,
        user_ids=[carol.id, org_admin.id],
        group_ids=[grp_finance.id],
        owner_id=org_admin.id,
    )

    for p in [proj_loan, proj_kyc, proj_finance]:
        projects_db[p.id] = p

    # Sync project_ids back to users
    for pid, users in [
        (proj_loan.id, [alice, bob, org_admin]),
        (proj_kyc.id, [alice, org_admin]),
        (proj_finance.id, [carol, org_admin]),
    ]:
        for u in users:
            if pid not in u.project_ids:
                u.project_ids.append(pid)

    print("Default IAM data seeded (users, groups, projects)")


def initialize_db():
    for t in DUMMY_TOOLS:
        tools_db[t["id"]] = Tool(**t)

    for a in DUMMY_AGENTS:
        agents_db[a["id"]] = Agent(**a)

    for tpl_data in TEMPLATE_WORKFLOWS:
        wf = _build_workflow(tpl_data)
        workflows_db[wf.id] = wf
        library_workflow_ids.add(wf.id)

    # Load persisted user workflows (must run after templates are seeded)
    from persistence import load_user_workflows
    load_user_workflows()

    # Seed IAM data (skipped if already loaded from disk by portal_persistence)
    _seed_iam()

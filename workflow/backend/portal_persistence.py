"""Persist IAM data (users, groups, projects) and reviews/audit logs."""
import json
from datetime import datetime

from models import UserInDB, Group, Project, AuditLog, ReviewItem, UserRole
from config import get_data_dir
import org_config

_DIR = get_data_dir()
_USERS_FILE = _DIR / "users.json"
_GROUPS_FILE = _DIR / "groups.json"
_PROJECTS_FILE = _DIR / "projects.json"
_REVIEWS_FILE = _DIR / "reviews.json"


def save_portal_data():
    from db import users_db, groups_db, projects_db, reviews_db
    _USERS_FILE.write_text(json.dumps([u.model_dump(mode="json") for u in users_db.values()], indent=2, default=str), encoding="utf-8")
    _GROUPS_FILE.write_text(json.dumps([g.model_dump(mode="json") for g in groups_db.values()], indent=2, default=str), encoding="utf-8")
    _PROJECTS_FILE.write_text(json.dumps([p.model_dump(mode="json") for p in projects_db.values()], indent=2, default=str), encoding="utf-8")
    _REVIEWS_FILE.write_text(json.dumps([r.model_dump(mode="json") for r in reviews_db.values()], indent=2, default=str), encoding="utf-8")


def load_portal_data():
    from db import users_db, groups_db, projects_db, reviews_db

    if _USERS_FILE.exists():
        try:
            records = json.loads(_USERS_FILE.read_text(encoding="utf-8"))
            users_db.clear()
            for ud in records:
                u = UserInDB(
                    id=ud["id"], email=org_config.apply_org_domain(ud["email"]), name=ud["name"],
                    password_hash=ud["password_hash"],
                    role=UserRole(ud["role"]),
                    group_ids=ud.get("group_ids", []),
                    project_ids=ud.get("project_ids", []),
                    is_active=ud.get("is_active", True),
                    avatar=ud.get("avatar"),
                    created_at=datetime.fromisoformat(ud["created_at"]) if "created_at" in ud else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(ud["updated_at"]) if "updated_at" in ud else datetime.utcnow(),
                )
                users_db[u.id] = u
            print(f"Loaded {len(records)} users from {_USERS_FILE.name}")
        except Exception as exc:
            print(f"Could not load users.json: {exc}")

    if _GROUPS_FILE.exists():
        try:
            records = json.loads(_GROUPS_FILE.read_text(encoding="utf-8"))
            groups_db.clear()
            for gd in records:
                g = Group(
                    id=gd["id"], name=gd["name"], description=gd.get("description", ""),
                    user_ids=gd.get("user_ids", []), project_ids=gd.get("project_ids", []),
                    is_active=gd.get("is_active", True),
                    created_at=datetime.fromisoformat(gd["created_at"]) if "created_at" in gd else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(gd["updated_at"]) if "updated_at" in gd else datetime.utcnow(),
                )
                groups_db[g.id] = g
            print(f"Loaded {len(records)} groups from {_GROUPS_FILE.name}")
        except Exception as exc:
            print(f"Could not load groups.json: {exc}")

    if _PROJECTS_FILE.exists():
        try:
            records = json.loads(_PROJECTS_FILE.read_text(encoding="utf-8"))
            projects_db.clear()
            for pd in records:
                p = Project(
                    id=pd["id"], name=pd["name"], description=pd.get("description", ""),
                    launchurl=pd.get("launchurl"),
                    workflow_ids=pd.get("workflow_ids", []),
                    user_ids=pd.get("user_ids", []),
                    group_ids=pd.get("group_ids", []),
                    owner_id=pd.get("owner_id"),
                    is_active=pd.get("is_active", True),
                    created_at=datetime.fromisoformat(pd["created_at"]) if "created_at" in pd else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(pd["updated_at"]) if "updated_at" in pd else datetime.utcnow(),
                )
                projects_db[p.id] = p
            print(f"Loaded {len(records)} projects from {_PROJECTS_FILE.name}")
        except Exception as exc:
            print(f"Could not load projects.json: {exc}")

    if _REVIEWS_FILE.exists():
        try:
            records = json.loads(_REVIEWS_FILE.read_text(encoding="utf-8"))
            reviews_db.clear()
            for rd in records:
                r = ReviewItem(
                    id=rd["id"], type=rd["type"], item_id=rd["item_id"],
                    item_name=rd["item_name"], status=rd["status"],
                    submitted_by_id=rd["submitted_by_id"],
                    submitted_by_name=rd["submitted_by_name"],
                    reviewed_by_id=rd.get("reviewed_by_id"),
                    reviewed_by_name=rd.get("reviewed_by_name"),
                    submitted_at=datetime.fromisoformat(rd["submitted_at"]) if "submitted_at" in rd else datetime.utcnow(),
                    reviewed_at=datetime.fromisoformat(rd["reviewed_at"]) if rd.get("reviewed_at") else None,
                    notes=rd.get("notes"),
                    item_data=rd.get("item_data", {}),
                )
                reviews_db[r.id] = r
            print(f"Loaded {len(records)} reviews from {_REVIEWS_FILE.name}")
        except Exception as exc:
            print(f"Could not load reviews.json: {exc}")

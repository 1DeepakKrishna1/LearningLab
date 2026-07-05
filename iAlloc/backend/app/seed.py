"""Idempotent database seeder.

Run with:  python -m app.seed
Creates the schema, a ProductAdmin, and a fully-configured & active
'National Entrance Exam (NTA)' system with demo stakeholders and applications.
"""
from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    AllocationOption,
    Application,
    ApplicationStatus,
    Evaluation,
    System,
    SystemDomain,
    SystemStatus,
    User,
    UserRole,
)
from app.services.config_builder import build_config, default_options
from app.services.workflow import init_stage_records

DEFAULT_PW = "Admin@123"


def _get_or_create_user(db: Session, email: str, full_name: str, role: UserRole,
                        system_id: int | None = None) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(
        email=email, full_name=full_name, role=role, system_id=system_id,
        hashed_password=hash_password(DEFAULT_PW),
    )
    db.add(user)
    db.flush()
    return user


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # 1. ProductAdmin
        product_admin = _get_or_create_user(
            db, "product.admin@ialloc.io", "Product Admin", UserRole.product_admin
        )

        # 2. NTA examination system
        system = db.scalar(select(System).where(System.key == "nta_jee"))
        if not system:
            system = System(
                key="nta_jee",
                name="National Entrance Exam (JEE)",
                domain=SystemDomain.examination,
                description="Reference deployment: registration → exam → evaluation → "
                "rank → counselling → seat allocation → admission.",
                status=SystemStatus.active,
                config=build_config("examination"),
                created_by=product_admin.id,
            )
            db.add(system)
            db.flush()
            for opt in default_options("examination"):
                db.add(
                    AllocationOption(
                        system_id=system.id, key=opt["key"], label=opt["label"],
                        capacity=opt.get("capacity", 0),
                    )
                )

        # 3. Stakeholders for the system
        _get_or_create_user(db, "nta.admin@ialloc.io", "NTA System Admin",
                            UserRole.system_admin, system.id)
        _get_or_create_user(db, "verifier@ialloc.io", "Doc Verifier",
                            UserRole.verifier, system.id)
        _get_or_create_user(db, "evaluator@ialloc.io", "Exam Evaluator",
                            UserRole.evaluator, system.id)
        _get_or_create_user(db, "allocator@ialloc.io", "Counselling Authority",
                            UserRole.allocation_authority, system.id)
        _get_or_create_user(db, "auditor@ialloc.io", "Auditor",
                            UserRole.auditor, system.id)
        _get_or_create_user(db, "reporting@ialloc.io", "Reporting Authority",
                            UserRole.reporting_authority, system.id)

        # 4. Demo applicants with applications + evaluations
        demo = [
            ("applicant@ialloc.io", "Asha Rao", 96.0, "GEN"),
            ("ben@ialloc.io", "Ben Kumar", 88.5, "OBC"),
            ("chitra@ialloc.io", "Chitra Nair", 91.0, "SC"),
        ]
        for email, name, marks, cat in demo:
            applicant = _get_or_create_user(db, email, name, UserRole.applicant, system.id)
            existing_app = db.scalar(
                select(Application).where(Application.applicant_id == applicant.id)
            )
            if existing_app:
                continue
            app = Application(
                system_id=system.id,
                applicant_id=applicant.id,
                reference_no=f"NTA_JEE-{secrets.token_hex(3).upper()}",
                status=ApplicationStatus.evaluated,
                data={"full_name": name, "qualifying_marks": marks, "category": cat,
                      "dob": "2007-05-15"},
            )
            db.add(app)
            db.flush()
            init_stage_records(db, app, system)
            db.add(
                Evaluation(
                    application_id=app.id, stage_key="evaluation",
                    score=marks, max_score=100.0,
                    criteria={"source": "seed"}, remarks="Seed evaluation",
                )
            )

        db.commit()
        print("Seed complete.")
        print(f"  ProductAdmin : product.admin@ialloc.io / {DEFAULT_PW}")
        print(f"  SystemAdmin  : nta.admin@ialloc.io / {DEFAULT_PW}")
        print(f"  Applicant    : applicant@ialloc.io / {DEFAULT_PW}")
        print(f"  Verifier     : verifier@ialloc.io / {DEFAULT_PW}")
        print(f"  Evaluator    : evaluator@ialloc.io / {DEFAULT_PW}")
        print(f"  Allocator    : allocator@ialloc.io / {DEFAULT_PW}")
        print(f"  Auditor      : auditor@ialloc.io / {DEFAULT_PW}")
        print(f"  System       : '{system.name}' (id={system.id}, key={system.key})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

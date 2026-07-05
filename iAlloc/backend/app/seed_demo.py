"""Demo seeder — one fully-configured ACTIVE system per domain in domains.json,
each populated with stakeholders and applications spread across the lifecycle so
every stakeholder has realistic data to act on at each stage.

Run with:  python -m app.seed_demo
Idempotent: a domain whose system key already exists is skipped.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    AIInvocation,
    Allocation,
    AllocationOption,
    Application,
    ApplicationStatus,
    Document,
    DocStatus,
    Evaluation,
    Payment,
    PaymentStatus,
    Preference,
    StageStatus,
    System,
    SystemDomain,
    SystemStatus,
    User,
    UserRole,
)
from app.services import allocation as allocation_svc
from app.services import ranking as ranking_svc
from app.services.config_builder import build_config, default_options, ordered_enabled_stages
from app.services.workflow import audit, complete_stage, init_stage_records

DEFAULT_PW = "Admin@123"

# The stakeholder roles provisioned for every demo system.
SYSTEM_STAFF = [
    (UserRole.system_admin, "admin", "System Admin"),
    (UserRole.verifier, "verifier", "Document Verifier"),
    (UserRole.evaluator, "evaluator", "Evaluator"),
    (UserRole.allocation_authority, "allocator", "Allocation Authority"),
    (UserRole.payment_agency, "payments", "Payment Agency"),
    (UserRole.auditor, "auditor", "Auditor"),
    (UserRole.support, "support", "Support Desk"),
    (UserRole.institution, "institution", "End Institution"),
    (UserRole.reporting_authority, "reporting", "Reporting Authority"),
]


# domain -> (system_key, system_name, description, [applicants])
# Each applicant: (full_name, data dict matching the domain form fields, score 0-100)
DEMOS: dict[str, dict] = {
    "examination": {
        "key": "cuet_ug_2026",
        "name": "CUET UG 2026",
        "desc": "Common University Entrance Test — registration to seat allocation.",
        "applicants": [
            ("Aarav Sharma", {"full_name": "Aarav Sharma", "dob": "2007-03-11", "category": "GEN", "qualifying_marks": 95}, 95),
            ("Diya Patel", {"full_name": "Diya Patel", "dob": "2007-08-22", "category": "OBC", "qualifying_marks": 91}, 91),
            ("Kabir Singh", {"full_name": "Kabir Singh", "dob": "2007-01-05", "category": "SC", "qualifying_marks": 88}, 88),
            ("Meera Iyer", {"full_name": "Meera Iyer", "dob": "2007-11-30", "category": "GEN", "qualifying_marks": 79}, 0),
            ("Rohan Das", {"full_name": "Rohan Das", "dob": "2007-06-14", "category": "EWS", "qualifying_marks": 72}, 0),
        ],
    },
    "university_admission": {
        "key": "du_admissions_2026",
        "name": "Delhi University Admissions 2026",
        "desc": "Undergraduate admission via entrance test and merit list.",
        "applicants": [
            ("Ishaan Verma", {"full_name": "Ishaan Verma", "program": "BSc Computer Science", "ug_percentage": 93}, 93),
            ("Ananya Rao", {"full_name": "Ananya Rao", "program": "BA Economics", "ug_percentage": 90}, 90),
            ("Vivaan Nair", {"full_name": "Vivaan Nair", "program": "BSc Computer Science", "ug_percentage": 85}, 85),
            ("Sara Khan", {"full_name": "Sara Khan", "program": "BA Economics", "ug_percentage": 80}, 0),
            ("Aditya Bose", {"full_name": "Aditya Bose", "program": "BSc Computer Science", "ug_percentage": 76}, 0),
        ],
    },
    "recruitment": {
        "key": "techcorp_hiring_2026",
        "name": "TechCorp Campus Hiring 2026",
        "desc": "Campus recruitment: application to offer with interview rounds.",
        "applicants": [
            ("Nisha Gupta", {"full_name": "Nisha Gupta", "cgpa": 9.2, "skills": "Python, ML"}, 92),
            ("Arjun Mehta", {"full_name": "Arjun Mehta", "cgpa": 8.8, "skills": "Java, Spring"}, 88),
            ("Tara Joshi", {"full_name": "Tara Joshi", "cgpa": 8.4, "skills": "React, Node"}, 84),
            ("Dev Malhotra", {"full_name": "Dev Malhotra", "cgpa": 7.9, "skills": "SQL, ETL"}, 0),
            ("Pooja Reddy", {"full_name": "Pooja Reddy", "cgpa": 7.5, "skills": "QA, Selenium"}, 0),
        ],
    },
    "scholarship": {
        "key": "merit_scholarship_2026",
        "name": "National Merit Scholarship 2026",
        "desc": "Means-cum-merit scholarship with fund disbursement.",
        "applicants": [
            ("Riya Kulkarni", {"full_name": "Riya Kulkarni", "family_income": 180000, "merit_score": 94}, 94),
            ("Aman Yadav", {"full_name": "Aman Yadav", "family_income": 150000, "merit_score": 89}, 89),
            ("Sneha Pillai", {"full_name": "Sneha Pillai", "family_income": 120000, "merit_score": 86}, 86),
            ("Karan Saxena", {"full_name": "Karan Saxena", "family_income": 250000, "merit_score": 78}, 0),
            ("Fatima Sheikh", {"full_name": "Fatima Sheikh", "family_income": 90000, "merit_score": 73}, 0),
        ],
    },
    "housing": {
        "key": "hostel_alloc_2026",
        "name": "University Hostel Allocation 2026",
        "desc": "Hostel room allocation by priority and preference.",
        "applicants": [
            ("Harsh Vyas", {"full_name": "Harsh Vyas", "distance_km": 420, "year_of_study": 1}, 90),
            ("Lavanya Menon", {"full_name": "Lavanya Menon", "distance_km": 350, "year_of_study": 2}, 85),
            ("Yash Agarwal", {"full_name": "Yash Agarwal", "distance_km": 300, "year_of_study": 1}, 80),
            ("Naina Chopra", {"full_name": "Naina Chopra", "distance_km": 120, "year_of_study": 3}, 0),
            ("Imran Ali", {"full_name": "Imran Ali", "distance_km": 60, "year_of_study": 2}, 0),
        ],
    },
    "govt_benefit": {
        "key": "crop_subsidy_2026",
        "name": "Crop Subsidy Scheme 2026",
        "desc": "Farmer subsidy distribution by eligibility and priority.",
        "applicants": [
            ("Ramesh Patil", {"full_name": "Ramesh Patil", "aadhaar_last4": "4821", "annual_income": 80000}, 95),
            ("Sunita Devi", {"full_name": "Sunita Devi", "aadhaar_last4": "1193", "annual_income": 95000}, 90),
            ("Govind Rao", {"full_name": "Govind Rao", "aadhaar_last4": "7720", "annual_income": 110000}, 85),
            ("Lakshmi Bai", {"full_name": "Lakshmi Bai", "aadhaar_last4": "3056", "annual_income": 130000}, 0),
            ("Mohan Lal", {"full_name": "Mohan Lal", "aadhaar_last4": "6644", "annual_income": 145000}, 0),
        ],
    },
    "tender": {
        "key": "amc_tender_2026",
        "name": "AMC Tender 2026",
        "desc": "Annual maintenance contract: bid submission to award.",
        "applicants": [
            ("Apex Facilities Pvt Ltd", {"vendor_name": "Apex Facilities Pvt Ltd", "technical_score": 92, "bid_amount": 4800000}, 92),
            ("BlueServ Solutions", {"vendor_name": "BlueServ Solutions", "technical_score": 88, "bid_amount": 4600000}, 88),
            ("CleanCorp India", {"vendor_name": "CleanCorp India", "technical_score": 83, "bid_amount": 4500000}, 83),
            ("DuraMaint LLP", {"vendor_name": "DuraMaint LLP", "technical_score": 77, "bid_amount": 5100000}, 0),
            ("EverCare Services", {"vendor_name": "EverCare Services", "technical_score": 70, "bid_amount": 5300000}, 0),
        ],
    },
    "generic": {
        "key": "generic_pilot",
        "name": "Generic Pilot Programme",
        "desc": "Blank canonical template for a brand-new allocation programme.",
        "applicants": [
            ("Test User One", {"full_name": "Test User One"}, 80),
            ("Test User Two", {"full_name": "Test User Two"}, 70),
            ("Test User Three", {"full_name": "Test User Three"}, 0),
        ],
    },
}


def _first_name(full: str) -> str:
    return full.split()[0].lower().replace(".", "")


def _get_or_create_user(db, email, full_name, role, system_id=None):
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(email=email, full_name=full_name, role=role, system_id=system_id,
                hashed_password=hash_password(DEFAULT_PW))
    db.add(user)
    db.flush()
    return user


def _add_documents(db, app, verified, verifier_id):
    for name, dtype, text in [
        ("ID Proof", "id_proof", "Government issued identity document."),
        ("Marksheet", "marksheet", "Qualifying examination marksheet."),
    ]:
        db.add(Document(
            application_id=app.id, name=name, doc_type=dtype, content_text=text,
            status=DocStatus.verified if verified else DocStatus.pending,
            verified_by=verifier_id if verified else None,
            remarks="Auto-verified (demo)" if verified else "",
        ))


def _ranking_index(stage_keys_types) -> int:
    for i, (_, t) in enumerate(stage_keys_types):
        if t in ("ranking", "allocation"):
            return i
    return len(stage_keys_types)


def seed_domain(db: Session, product_admin_id: int, domain: str, spec: dict) -> System | None:
    if db.scalar(select(System).where(System.key == spec["key"])):
        print(f"  - {domain}: '{spec['key']}' already exists, skipped")
        return None

    sysdomain = SystemDomain(domain) if domain in SystemDomain._value2member_map_ else SystemDomain.generic
    system = System(
        key=spec["key"], name=spec["name"], domain=sysdomain,
        description=spec["desc"], status=SystemStatus.active,
        config=build_config(domain), created_by=product_admin_id,
    )
    db.add(system)
    db.flush()

    for opt in default_options(domain):
        db.add(AllocationOption(system_id=system.id, key=opt["key"], label=opt["label"],
                                capacity=opt.get("capacity", 0)))
    db.flush()
    options = db.scalars(select(AllocationOption).where(AllocationOption.system_id == system.id)).all()

    # Stakeholders
    staff = {}
    for role, prefix, label in SYSTEM_STAFF:
        u = _get_or_create_user(db, f"{prefix}.{spec['key']}@demo.ialloc.io",
                                f"{label} — {system.name}", role, system.id)
        staff[role] = u
    verifier_id = staff[UserRole.verifier].id

    stages = ordered_enabled_stages(system.config or {})
    stage_kt = [(s["key"], s["type"]) for s in stages]
    rank_idx = _ranking_index(stage_kt)
    pre_rank_keys = [k for k, _ in stage_kt[:rank_idx]]

    applicants = spec["applicants"]
    n = len(applicants)
    for i, (name, data, score) in enumerate(applicants):
        applicant = _get_or_create_user(
            db, f"{_first_name(name)}.{spec['key']}@demo.ialloc.io", name,
            UserRole.applicant, system.id,
        )
        app = Application(
            system_id=system.id, applicant_id=applicant.id,
            reference_no=f"{spec['key'][:6].upper()}-{secrets.token_hex(3).upper()}",
            data=data, status=ApplicationStatus.in_progress,
        )
        db.add(app)
        db.flush()
        init_stage_records(db, app, system)
        db.flush()

        # Distribution: last = early (docs pending), 2nd-last = mid (eligible),
        # the rest = high (evaluated, ranked, allocated).
        if i == n - 1:
            tier = "low"
        elif i == n - 2:
            tier = "mid"
        else:
            tier = "high"

        if tier == "low":
            _add_documents(db, app, verified=False, verifier_id=verifier_id)
            if pre_rank_keys:
                complete_stage(db, app, system, pre_rank_keys[0], actor_id=applicant.id,
                               remarks="Registered")
            app.status = ApplicationStatus.in_progress
        elif tier == "mid":
            # Documents verified and eligibility cleared, but evaluation pending —
            # sits in the evaluator's queue and is not yet ranked.
            _add_documents(db, app, verified=True, verifier_id=verifier_id)
            for k in pre_rank_keys[: min(3, len(pre_rank_keys))]:
                complete_stage(db, app, system, k, actor_id=staff[UserRole.verifier].id,
                               remarks="Verified")
            app.status = ApplicationStatus.in_progress
        else:  # high
            _add_documents(db, app, verified=True, verifier_id=verifier_id)
            db.add(Evaluation(application_id=app.id, stage_key="evaluation",
                              evaluator_id=staff[UserRole.evaluator].id,
                              score=score, max_score=100.0,
                              criteria={"source": "demo"}, remarks="Demo evaluation"))
            # Preferences over available options
            for p, opt in enumerate(options[:3], start=1):
                db.add(Preference(application_id=app.id, option_key=opt.key,
                                  option_label=opt.label, priority=p))
            for k in pre_rank_keys:
                complete_stage(db, app, system, k, actor_id=staff[UserRole.evaluator].id,
                               remarks="Processed")
            app.status = ApplicationStatus.evaluated

    db.flush()

    # Merit ranking + allocation
    ranking_svc.generate_ranking(db, system)
    result = allocation_svc.run_allocation(db, system, actor_id=staff[UserRole.allocation_authority].id)

    # Accept top allocations -> enrolled + paid; leave others allotted/pending
    allocs = db.scalars(
        select(Allocation)
        .join(Application, Allocation.application_id == Application.id)
        .where(Application.system_id == system.id)
        .order_by(Application.rank)
    ).all()
    for idx, al in enumerate(allocs):
        app = db.get(Application, al.application_id)
        if idx < max(1, len(allocs) // 2):
            al.status = "accepted"
            app.status = ApplicationStatus.enrolled
            db.add(Payment(application_id=app.id, amount=1000.0, currency="INR",
                           purpose="admission_fee", status=PaymentStatus.paid,
                           reference=f"PAY-{secrets.token_hex(4).upper()}",
                           paid_at=datetime.now(timezone.utc)))
        else:
            db.add(Payment(application_id=app.id, amount=1000.0, currency="INR",
                           purpose="admission_fee", status=PaymentStatus.pending,
                           reference=f"PAY-{secrets.token_hex(4).upper()}"))

    # A sample AI invocation so the AI Activity log is populated for demos.
    db.add(AIInvocation(
        system_id=system.id, stage_key="eligibility", task="assess_eligibility",
        user_id=staff[UserRole.verifier].id, model="llama-3.3-70b-versatile",
        prompt="Assess eligibility for applicant against the 2026 criteria.",
        response="Recommendation: ELIGIBLE. The applicant meets the qualifying "
                 "threshold and submitted all mandatory documents. (Sample log entry — "
                 "a human verifier makes the final decision.)",
        tokens=128,
    ))

    audit(db, system_id=system.id, actor_id=product_admin_id, action="demo_seeded",
          entity_type="system", entity_id=system.id, detail=result)
    db.commit()
    print(f"  + {domain}: '{system.name}' (key={system.key}, id={system.id}) - "
          f"{n} applicants, {result['allotted']} allotted")
    return system


def seed_demo() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        product_admin = _get_or_create_user(
            db, "product.admin@ialloc.io", "Product Admin", UserRole.product_admin
        )
        db.commit()
        print("Seeding one demo system per domain...")
        created = []
        for domain, spec in DEMOS.items():
            sys = seed_domain(db, product_admin.id, domain, spec)
            if sys:
                created.append(spec)

        print("\nDemo seed complete.")
        print(f"  ProductAdmin: product.admin@ialloc.io / {DEFAULT_PW}")
        print("\n  Per-system stakeholder logins (password Admin@123):")
        print("    <role>.<system_key>@demo.ialloc.io")
        print("    roles: admin, verifier, evaluator, allocator, payments, auditor,")
        print("           support, institution, reporting")
        print("    applicants: <firstname>.<system_key>@demo.ialloc.io")
        if created:
            ex = created[0]["key"]
            print(f"\n  Example for '{ex}':")
            print(f"    SystemAdmin : admin.{ex}@demo.ialloc.io")
            print(f"    Verifier    : verifier.{ex}@demo.ialloc.io")
            print(f"    Evaluator   : evaluator.{ex}@demo.ialloc.io")
            print(f"    Allocator   : allocator.{ex}@demo.ialloc.io")
            print(f"    Applicant   : {_first_name(DEMOS[list(DEMOS)[0]]['applicants'][0][0])}.{ex}@demo.ialloc.io")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()

# iAlloc — Generalized Application→Allocation Enterprise Platform

iAlloc is a single, **config-driven** platform that models the common
*application → examination → evaluation → ranking → allocation → enrollment*
lifecycle described in `iAlloc.pdf`. Instead of building six separate products,
every domain (national examinations, university admissions, recruitment,
scholarships, hostel/housing allocation, government benefits, tenders) is a
**JSON-configured instance** of one canonical 14-stage engine.

```
Notification → Registration → Document Mgmt → Eligibility → Scheduling →
Assessment → Evaluation → Ranking → Preference → Allocation → Payment →
Verification → Enrollment → Closure & Analytics
```

## Roles

| Role | Scope | Capability |
|------|-------|-----------|
| **ProductAdmin** | Global | Create/configure Systems, provision SystemAdmins |
| **SystemAdmin** | Per-system | Configure stages, assign stakeholder roles, toggle AI per stage |
| **Applicant** | Per-system | Register, apply, upload docs, set preferences, pay, enroll |
| **Verifier** | Per-system | Verify documents / data |
| **Evaluator** | Per-system | Score assessments |
| **AllocationAuthority** | Per-system | Generate merit list, run allocation engine |
| **PaymentAgency** | Per-system | Reconcile payments |
| **Auditor** | Per-system | Read-only audit trail |
| **Support / Institution / ReportingAuthority** | Per-system | Helpdesk / onboarding / analytics |

Any stakeholder can invoke **Groq-powered AI assistance** at any stage the
SystemAdmin has enabled it for.

## Tech stack

- **Frontend:** React (Vite) + React Router + Axios
- **Backend:** FastAPI + SQLAlchemy
- **Storage:** MySQL
- **Configuration:** JSON (stage definitions, form fields, AI settings)
- **LLM:** Groq (OpenAI-compatible chat completions)

## Quick start

### 1. MySQL (local instance)
Use your locally installed MySQL on `localhost:3306`. The default connection
string expects user `root` / password `admin` (override via `DATABASE_URL` in
`.env`). Create the database once:
```bash
mysql -u root -padmin -e "CREATE DATABASE IF NOT EXISTS ialloc CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```
> _Optional:_ a `docker-compose.yml` is included if you'd rather run MySQL in a
> container (`docker compose up -d db`) — just update `DATABASE_URL` to match.

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env           # default DB = mysql+pymysql://root:admin@localhost:3306/ialloc; set GROQ_API_KEY
python -m app.seed             # creates tables + ProductAdmin + seeded NTA system
uvicorn app.main:app --reload  # http://localhost:8000  (docs at /docs)
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

### Demo logins (created by seed)
| Role | Email | Password |
|------|-------|----------|
| ProductAdmin | product.admin@ialloc.io | Admin@123 |
| SystemAdmin (NTA) | nta.admin@ialloc.io | Admin@123 |
| Applicant | applicant@ialloc.io | Admin@123 |
| Verifier | verifier@ialloc.io | Admin@123 |
| Evaluator | evaluator@ialloc.io | Admin@123 |
| AllocationAuthority | allocator@ialloc.io | Admin@123 |
| Auditor | auditor@ialloc.io | Admin@123 |

### Optional: seed ALL domains with rich demo data
```bash
python -m app.seed_demo    # one active system per domain, populated across all stages
```
This creates a fully-configured **active system for every domain** in `domains.json`
(examination, university admission, recruitment, scholarship, housing, government
benefit, tender, and a generic pilot), each with:
- a full stakeholder team (SystemAdmin, Verifier, Evaluator, AllocationAuthority,
  PaymentAgency, Auditor, Support, Institution, ReportingAuthority),
- 3–5 applicants spread across the lifecycle — some `in_progress` with **pending
  documents** (verifier queue), some awaiting **evaluation** (evaluator queue), and
  some **evaluated → ranked → allocated → enrolled** (with payments and a sample AI log).

**Login convention** (password `Admin@123`):
```
<role>.<system_key>@demo.ialloc.io      # role ∈ admin,verifier,evaluator,allocator,
                                        #        payments,auditor,support,institution,reporting
<firstname>.<system_key>@demo.ialloc.io # applicants
```
Example for CUET (`cuet_ug_2026`): `admin.cuet_ug_2026@demo.ialloc.io`,
`verifier.cuet_ug_2026@demo.ialloc.io`, `aarav.cuet_ug_2026@demo.ialloc.io`.

## Adding a new domain
ProductAdmin → *Create System* → pick a domain template (or the blank canonical
template) → a SystemAdmin is provisioned → SystemAdmin enables/disables stages,
edits form fields, and turns AI on per stage. No code changes required.

See `docs/ARCHITECTURE.md` for the full design.

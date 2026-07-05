# iAlloc Architecture

## 1. The core idea: one engine, many domains

`iAlloc.pdf` shows that national exams, university admissions, recruitment,
scholarships, hostel allocation, government benefits and tenders are all the
**same lifecycle** with different labels:

```
Notification → Registration → Document Mgmt → Eligibility → Scheduling →
Assessment → Evaluation → Ranking → Preference → Allocation → Payment →
Verification → Enrollment → Closure & Analytics
```

iAlloc implements this once as a **config-driven engine**. A *System* is a JSON
configuration over the 14-stage **stage catalog**. Creating a new domain is data,
not code.

```
ProductAdmin ──creates──► System (JSON config) ──provisions──► SystemAdmin
                                  │                                   │
                                  │ enables/disables stages,          │ configures stages,
                                  │ form fields, AI per stage         │ manages stakeholders,
                                  ▼                                   ▼ allocation options
                          Stakeholders (Applicant, Verifier, Evaluator,
                          AllocationAuthority, Auditor, …) act on stages,
                          with optional Groq AI assist where enabled.
```

## 2. Configuration model (`System.config`, JSON)

```jsonc
{
  "domain": "examination",
  "stages": [
    {
      "key": "eligibility",
      "type": "eligibility",
      "name": "Eligibility Verification",
      "order": 4,
      "enabled": true,
      "roles": ["verifier"],
      "ai": { "enabled": true, "task": "assess_eligibility",
              "model": null, "instructions": "Min 75% in Class 12." },
      "available_ai_tasks": ["assess_eligibility", "explain_decision"]
    }
    // … 13 more
  ],
  "form_fields": [ { "key": "dob", "label": "Date of Birth", "type": "date", "required": true } ],
  "ranking":    { "strategy": "score_desc", "tie_breakers": ["dob_asc"] },
  "allocation": { "strategy": "merit_preference", "rounds": 1 }
}
```

- **Catalog** (`backend/app/config_templates/catalog.json`) — the 14 canonical stage
  types, their default roles, and the AI tasks available per type + prompt library.
- **Domain templates** (`domains.json`) — which stages each of the 7 domains turns
  on, with name overrides, default form fields and allocation options.
- `services/config_builder.py` materializes a full config from catalog + template.

## 3. Backend (FastAPI)

| Layer | Location |
|-------|----------|
| Config / DB / JWT | `app/core/` |
| ORM models | `app/models/models.py` |
| Pydantic schemas | `app/schemas/schemas.py` |
| Engines | `app/services/` — `config_builder`, `ranking`, `allocation`, `workflow`, `ai` |
| HTTP routers | `app/api/routers/` |

### Routers
- `auth` — login, OAuth2 token, self-registration, `/me`
- `product_admin` (`/api/admin`) — domain templates, system CRUD, provisioning, overview
- `system_admin` (`/api/systems/{id}/admin`) — stage config, AI toggles, options, members
- `systems` — public listing + stage/option reads
- `applications` — apply, documents, preferences, payments, allocation responses, stage actions
- `staff` (`/api/systems/{id}/staff`) — verification, eligibility, evaluation, ranking, allocation
- `ai` (`/api/ai`) — generic stage-aware Groq assist + invocation log
- `reports` (`/api/systems/{id}/reports`) — summary + audit trail

### AuthZ
JWT carries `sub` (user id), `role`, `system_id`. Dependencies in `api/deps.py`
enforce: ProductAdmin is global; everyone else is scoped to their `system_id`.
`require_roles(...)` gates each endpoint.

## 4. The allocation engine (`services/allocation.py`)

Capacity-aware, deterministic, idempotent per round:
- `merit_preference` — candidates in rank order receive their highest-priority
  preference with remaining capacity (seats/jobs/rooms).
- `merit_priority` — rank order fills options in order (funds/subsidies).

Ranking (`services/ranking.py`) aggregates evaluation scores (normalized 0–100,
averaged), falls back to a merit-bearing form field, then applies the configured
strategy + tie-breakers to assign dense ranks.

## 5. AI integration (`services/ai.py`, Groq)

A single `run_stage_ai()` entry point:
1. Looks up the stage's `ai` config; refuses if not enabled.
2. Builds a system prompt from the task's prompt template + admin instructions.
3. Assembles **live context** (application data, documents, evaluations, options,
   preferences) relevant to the stage type.
4. Calls Groq's OpenAI-compatible `chat/completions`.
5. Logs an `AIInvocation` row for audit.

AI is strictly **advisory** — every prompt instructs the model that a human makes
the final decision. If `GROQ_API_KEY` is unset, the API returns a clear message
and the UI shows "no API key".

## 6. Frontend (React + Vite)

- `auth/AuthContext` — token + user persistence, login/register/logout.
- `components/Layout` — role-driven sidebar navigation.
- `components/StageConfigEditor` — shared stage/AI configuration (ProductAdmin & SystemAdmin).
- `components/AIAssist` — reusable panel rendered only on AI-enabled stages.
- Role landing pages: ProductAdmin overview/create/detail, SystemAdmin config/
  members/options/reports/AI-logs, Applicant apply/detail, Staff workspace.

## 7. Extending

- **New domain:** add an entry to `domains.json`. No code change.
- **New AI task:** add a prompt to `catalog.json` `ai_task_prompts` and list it
  under the relevant stage type's `ai_tasks`.
- **New stakeholder role:** add to `UserRole` enum + nav map.

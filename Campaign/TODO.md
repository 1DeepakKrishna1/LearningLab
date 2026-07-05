# TODO — Campaign Management Platform

Outstanding work to take the current build from a complete, runnable foundation to a
fully production-hardened platform. Items are grouped by priority. Each references the
relevant file(s) so a developer can start immediately.

**Legend:** 🔴 high · 🟠 medium · 🟢 low · `path:line` = exact inline `TODO` marker.

> Current state: all 18 modules functional end-to-end; console/sandbox providers;
> 16 backend tests + frontend build passing. See [docs/DESIGN.md](docs/DESIGN.md) §17 roadmap & §19 risks.

---

## 1. Provider integrations (real / live mode)

- 🔴 **FCM live send** — implement Firebase Cloud Messaging HTTP v1 send using a
  service-account OAuth2 token. Currently falls back to sandbox.
  `backend/app/providers/fcm.py:27` · add `firebase-admin` from `requirements.txt` commented block.
- 🔴 **OneSignal live send** — `POST https://onesignal.com/api/v1/notifications` with the REST API key.
  `backend/app/providers/fcm.py:49`.
- 🟠 **SendGrid health check** — ping `GET /v3/scopes` instead of just checking key presence.
  `backend/app/providers/sendgrid.py:50`.
- 🟠 **Twilio health check** — `GET` the account resource for a real connectivity check.
  `backend/app/providers/twilio.py:40`.
- 🟠 **Inbound provider webhooks** — map vendor delivery/bounce/complaint callbacks into
  `POST /api/v1/events/ingest` (SendGrid event webhook, Twilio status callback, FCM/OneSignal
  receipts) so tracking reflects real async outcomes, not just synthetic events.
  Bridge endpoint exists: `backend/app/api/v1/events.py`.
- 🟢 **Provider config CRUD in UI** — the Providers page is read-only + health check; add
  create/edit/delete forms (API already supports them: `backend/app/api/v1/providers.py`).
  `frontend/src/pages/ProviderConfiguration.tsx`.

## 2. Campaign execution depth

- 🔴 **True drip timing** — `delay_hours` is modeled but steps currently send sequentially.
  Schedule future steps via the scheduler (per-step `next_run_at`) instead of in one pass.
  `backend/app/execution/engine.py:177` (`TODO(drip)`).
- 🟠 **Recurrence robustness** — monthly recurrence is simplified to +30 days; use proper
  calendar math (e.g. `dateutil.relativedelta`) and add `BYDAY`/end-date handling.
  `backend/app/execution/scheduler.py` (`_compute_next_run`).
- 🟠 **Timezone-aware sends** — honor each campaign's `timezone` (and optionally per-contact
  timezone) when computing due time, rather than treating `scheduled_at` as UTC-naive.
  `backend/app/execution/scheduler.py`, `backend/app/models/models.py` (Campaign.timezone).
- 🟠 **Rate limiting in the engine** — `RATE_LIMIT_PER_SECOND` is configured in
  `data/config/campaign.json` but not enforced during sends; add a token-bucket throttle
  between provider calls. `backend/app/execution/engine.py`.
- 🟢 **Resume after crash** — on startup, reconcile campaigns stuck in `sending` (re-queue
  pending deliveries idempotently). `backend/app/main.py` lifespan + `engine.py`.

## 3. Auth & security hardening

- 🔴 **Email delivery for password reset** — reset token is currently logged, not emailed.
  Route it through the configured email provider. `backend/app/api/v1/auth.py:126`.
- 🟠 **Password policy enforcement** — `data/config/security.json` declares a policy
  (uppercase/number/etc.) but only min-length is enforced. Add a Pydantic validator.
  `backend/app/schemas/auth.py`, `backend/app/schemas/user.py`.
- 🟠 **Shared rate limiter** — in-memory limiter is per-process; swap to Redis for
  multi-worker deployments (keep the `hit()` API). `backend/app/core/rate_limit.py`.
- 🟠 **HSTS / TLS** — enable HSTS header and document reverse-proxy TLS termination for prod
  (currently off for local). `backend/app/core/middleware.py`, `data/config/security.json`.
- 🟢 **Refresh-token cleanup job** — periodically purge expired/revoked rows from
  `refresh_tokens`. New scheduled task in `backend/app/execution/scheduler.py`.

## 4. Reporting & analytics scale

- 🔴 **Analytics rollup job** — populate `analytics_snapshots` daily so dashboards query
  rollups instead of scanning `event_logs` (needed for 1M contacts / 500k msgs/day).
  New job in scheduler; consume in `backend/app/services/analytics_service.py`.
- 🟠 **Scheduled reports execution** — `reports.schedule` (daily/weekly/monthly) is stored
  but not auto-generated; add a scheduler task that renders + persists report files.
  `backend/app/api/v1/reports.py`, `backend/app/services/report_service.py`, scheduler.
- 🟢 **Report filters** — apply `Report.filters` (date range, campaign, channel) in
  `report_service.generate` (currently exports all campaigns).
- 🟢 **Per-channel overview** — populate `OverviewMetrics.by_channel` (currently empty).
  `backend/app/services/analytics_service.py` (`overview`).

## 5. Data & scale

- 🟠 **Streamed CSV import** — current import loads the whole file into memory; stream rows
  and commit in batches for large files. `backend/app/api/v1/contacts.py` (`import_contacts_csv`).
- 🟠 **Postgres option** — code is DB-agnostic via SQLAlchemy; validate the
  `json_extract`/`strftime` SQLite-isms (segment engine, analytics) have Postgres equivalents
  and gate them by dialect. `backend/app/services/segment_engine.py`, `analytics_service.py`.
- 🟢 **Nested segment groups in UI** — backend supports nested AND/OR rule groups; the
  builder UI only edits a flat list. `frontend/src/pages/SegmentBuilder.tsx`.
- 🟢 **Custom-field-driven UI** — surface `contact_custom_fields` as dynamic inputs in the
  contact editor and as segment fields. `frontend/src/pages/ContactManagement.tsx`.

## 6. Frontend gaps

- 🟠 **Code-splitting** — main bundle is ~1.4 MB; add route-level `React.lazy` + dynamic
  imports / `manualChunks`. `frontend/vite.config.ts`, `frontend/src/App.tsx`.
- 🟢 **Template preview in UI** — wire the existing `POST /templates/{id}/preview` endpoint
  into a preview pane. `frontend/src/pages/TemplateLibrary.tsx`.
- 🟢 **Deliveries/events tab** — show per-campaign deliveries + event log on the details page
  (APIs exist: `/campaigns/{id}/deliveries`, `/events`). `frontend/src/pages/CampaignDetails.tsx`.
- 🟢 **Toasts & optimistic UI** — replace inline alerts with a global snackbar; add optimistic
  updates on mutations.
- 🟢 **Real calendar grid** — current calendar is a month-grouped list; integrate a calendar
  component if a true grid is desired. `frontend/src/pages/CampaignCalendar.tsx`.

## 7. Testing

- 🟠 **Frontend tests** — add component/e2e tests (Vitest + Testing Library, or Playwright for
  the login → build → send flow). None exist yet beyond the typecheck/build.
- 🟠 **Security tests** — rate-limit enforcement, injection/fuzz on segment rules, token
  tampering. Extend `backend/tests/`.
- 🟢 **Provider live-mode tests** — mock httpx/SMTP for SendGrid/Twilio/SMTP live paths.
- 🟢 **Load test** — validate the NFR targets (1k concurrent users, 500k msgs/day) with Locust/k6.

## 8. Packaging & DevOps

- 🟠 **Dockerfiles + docker-compose** — one container per tier (backend + static frontend),
  compose for one-command local run. (Repo root.)
- 🟠 **CI pipeline** — GitHub Actions: `pytest`, `npm run build`, ruff/eslint, alembic check.
- 🟢 **Production server config** — Uvicorn workers behind a reverse proxy; run scheduler on
  exactly one worker (env flag exists: `ENABLE_SCHEDULER`). Document in `docs/DESIGN.md` §15.
- 🟢 **Secrets management** — document moving `SECRET_KEY` + provider creds out of `.env`/JSON
  into a secret manager for production.
- 🟢 **Observability** — structured logs → metrics/tracing (OpenTelemetry), `/metrics` endpoint.

## 9. Compliance polish

- 🟢 **Unsubscribe link injection** — auto-append a tracked unsubscribe link/footer to email
  sends (CAN-SPAM). `backend/app/execution/engine.py` + `template_service`.
- 🟢 **Consent enforcement audit** — log suppressed (`skipped`) sends with reason for GDPR/TCPA
  evidence (already set on Delivery; surface in audit/report).
- 🟢 **Data export/erasure** — GDPR subject-access + right-to-be-forgotten endpoints for contacts.

---

### Quick reference — inline code TODOs
| File | Line | Item |
|------|------|------|
| `backend/app/execution/engine.py` | 177 | Drip: schedule delayed steps |
| `backend/app/api/v1/auth.py` | 126 | Email the password-reset token |
| `backend/app/providers/fcm.py` | 27 | FCM live HTTP v1 send |
| `backend/app/providers/fcm.py` | 49 | OneSignal live send |
| `backend/app/providers/sendgrid.py` | 50 | Real SendGrid health check |
| `backend/app/providers/twilio.py` | 40 | Real Twilio health check |

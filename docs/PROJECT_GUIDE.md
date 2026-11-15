# Project Guide

This document describes the current implementation and how to work with it.
It distinguishes implemented behavior from planned or demo-only behavior; a
folder or configuration setting does not by itself mean a service is ready
for deployment.

## System overview

```text
Browser -> React feature page -> shared API client -> FastAPI route
         -> permission/scope check -> service -> SQLAlchemy -> PostgreSQL

Campaign creation -> saved eligibility snapshot (no outbound calls)
Future approved call -> standalone voice-agent service (not wired in)
```

### Backend (`backend/`)

FastAPI routes use SQLAlchemy models, Pydantic schemas, and service-layer
business rules. The backend includes authentication and permission/scope
checks, attendance imports, attendance and campaign workflows, calls,
conversations, follow-ups, reports, and Alembic migrations. PostgreSQL is
required for a realistic local run. Read
[`BACKEND_ARCHITECTURE_GUIDE.md`](BACKEND_ARCHITECTURE_GUIDE.md) for the API
and data-flow details.

### Frontend (`frontend/`)

React 19 and Vite provide a responsive dashboard. Login, session restoration,
dashboard summary, class management, student listing/creation, attendance
imports, and campaign creation use the backend API. Frontend API calls are
centralized in `frontend/src/api/client.js`; feature screens are separated
under `frontend/src/features/`. Calls are explicitly not triggered by
campaign creation. Some backend workflows do not yet have frontend screens.

### ML scaffold (`ml/`)

The current files provide Pydantic request/response schemas, feature
extraction helpers, and model-related settings. There is no runnable FastAPI
application, trained model artifact, training/evaluation pipeline, or ML
test suite in this component. ML settings and schemas are not proof that
predictions are available.

### Voice agent (`voice-agent/`)

This is a separate FastAPI service that can originate and manage calls when
Twilio and AI-provider configuration, database migrations, network
connectivity, and explicit safety gates are in place. Its own detailed
instructions are in [`voice-agent/README.md`](../voice-agent/README.md).
Backend campaign dispatch does not currently invoke it; do not enable real
calls without completing the integration and its authorization checks.

## Prerequisites

- Windows PowerShell examples below assume Python 3.13 and Node.js/npm are
  installed.
- A local PostgreSQL instance and a database/user for the backend. The
  standalone voice service also needs its own configured database URL and
  migrations if you run it.
- External Twilio, Deepgram, Groq, and Cartesia accounts only if testing the
  voice service beyond its mocked/unit tests.

Python versions and provider model availability should be rechecked when
upgrading dependencies or deploying. Do not put credentials in source,
documentation, shell history, screenshots, or issue reports.

## Backend setup

From the repository root:

```powershell
Set-Location .\backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Set a PostgreSQL `DATABASE_URL` and a unique, high-entropy
`JWT_SECRET_KEY` in `backend/.env`; review all other settings in
`backend/.env.example`. Do not reuse the example secret or expose the file.
Then run:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

After migrating a **new, empty** database, create its first administrator
using `.\.venv\Scripts\python.exe -m app.bootstrap_admin`. The command refuses
to run after any user exists and requires a 14-character minimum password.
The interactive API reference is available at
`http://127.0.0.1:8000/docs` in development. Interactive API documentation is
disabled when `ENVIRONMENT=production`. Use the API's actual authentication,
authorization, and scope requirements; hiding a UI control is not access
control. Consult the backend guide before generating or applying migrations.

### Attendance imports

The backend import workflow supports `.xlsx`, `.xls`, `.csv`, PDF tables, and
DOCX tables, subject to its validation and file-size limits. Review the
required student identifiers, date columns, attendance markers, class/scope,
and percentage behavior in the backend architecture guide before preparing
production files. The frontend import screen sends files to this backend
workflow and displays the validation summary.

## Frontend setup and checks

```powershell
Set-Location .\frontend
npm ci
npm run dev
npm run lint
npm run build
```

Vite prints the local development URL after startup. `npm run build` writes
the deployable static bundle to `frontend/dist/`; `npm run preview` can serve
that bundle locally. There is currently no automated browser/component test
script in `package.json`; backend tests and frontend quality checks run in CI.

## Voice-agent setup

Read [`voice-agent/README.md`](../voice-agent/README.md) for complete provider
configuration, migration, webhook, and call instructions. In summary:

1. Install the service dependencies from `voice-agent/`.
2. Copy `.env.example` to `.env` and set credentials locally.
3. Apply the documented SQL migrations to the configured PostgreSQL database.
4. Keep `REAL_CALLS_ENABLED` and `EXTERNAL_AI_PROCESSING_APPROVED` false for
   ordinary development and automated tests.
5. Expose a public HTTPS/WSS endpoint only when the Twilio webhook setup,
   authentication, network controls, and privacy review are complete.
6. Require explicit parent-contact authorization and a unique idempotency
   key for every call request.

Call audio is not stored by the documented flow, but call context and
responses are persisted. Define and enforce a retention/deletion policy
before real use. The voice README also documents the guardian verification
and uncertainty/fail-closed behavior.

## ML service status

There is no service entry point to run yet. Before treating `ml/` as an
available service, implement and test at least:

1. A FastAPI app, health/readiness endpoints, and versioned prediction routes.
2. Versioned training data contracts, leakage-safe splits, reproducible
   training, validation metrics, calibration, and saved model artifacts.
3. Input bounds, missing/unknown feature handling, model-loading errors, and
   artifact compatibility checks.
4. Tests for feature extraction, schema validation, model inference, and
   service error behavior.
5. Model provenance, monitoring, privacy controls, and a documented rollback
   path. Keep outputs advisory; backend policy must make consequential
   decisions.

## Docker deployment

The root `deploy/compose.yml` runs PostgreSQL, the API, and the static
frontend. Copy `deploy/compose.env.example` to the ignored `deploy/.env`,
replace its placeholders, and follow the root README. The backend applies
Alembic migrations during container startup. The database is on an internal
Compose network and is not published to the host. The unprivileged Nginx
container serves the frontend and proxies API requests to the backend. Both
application containers use a read-only filesystem where practical,
`no-new-privileges`, health checks, and the frontend adds security response
headers plus a sign-in rate limit.

This is a portable starting point, not an unattended public-cloud release.
Place the host behind HTTPS, configure firewall/domain/DNS, verify production
secrets, backups and restoration, monitoring, and institutional privacy
approval. Real calling and the experimental ML scaffold are not deployed by
this Compose file.

## Tests and quality gates

Run from the repository root:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe -m pytest tests -q

Set-Location ..\voice-agent
.\.venv\Scripts\python.exe -m pytest tests -q

Set-Location ..\frontend
npm run lint
npm run build
```

The backend and voice-agent test suites use local mocks/fixtures where
appropriate; passing them does not verify telecom or AI-provider connectivity.
The CI workflow runs PostgreSQL migrations in a temporary PostgreSQL
container. Add browser tests and ML tests when those components gain behavior.

## Configuration and secret handling

- Each service has a checked-in `.env.example`; create an untracked `.env`
  locally and replace all placeholder values.
- `.env` files are ignored by Git. Never remove this protection or commit a
  local environment file.
- Use separate least-privilege credentials per service and environment.
- Rotate credentials if they were ever committed, shared, or included in
  logs; deleting a file in a later commit does not revoke a credential.
- Use a managed secrets store and TLS for deployed services.

## Deployment

No repository-wide Docker Compose deployment, CI release pipeline, or
production environment provisioning is currently documented. Deploy the
components separately only after the open items in
[`RELEASE_READINESS.md`](RELEASE_READINESS.md) are closed. Configure
production CORS/origins, TLS, database backups and migrations, health checks,
structured logs, alerting, rate limits, secret rotation, and rollback plans.
Do not expose a development server or the call API directly to the public
internet.

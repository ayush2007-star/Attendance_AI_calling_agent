# Attendance AI Agent Backend Guide

## Purpose

The backend is the source of truth for attendance, eligibility, campaigns, calls, conversations, transcripts, AI recommendations, and follow-ups. The frontend, voice agent, and future ML service must use backend APIs rather than writing directly to PostgreSQL.

## Request Flow

```text
HTTP request
  -> authentication
  -> database-backed permission check
  -> scope-aware service
  -> SQLAlchemy transaction
  -> Pydantic response schema
```

Routes should remain thin. Services own business rules. Models own database structure. Schemas define API contracts.

## Authorization

JWT authentication identifies the user. The backend reloads the user from PostgreSQL and rejects missing, invalid, expired, or inactive credentials.

Permissions are stored in:

- `roles`
- `permissions`
- `role_permissions`
- `user_roles`

Academic access is stored in:

- `scopes`
- `user_scopes`
- `classes.scope_id`

Students inherit access through their class. A user cannot access another scope merely because the frontend hides that data.

The reusable dependency is `require_permission(...)` in `app/api/dependencies.py`. Services also apply scope predicates, which protects non-HTTP callers and background workers.

## Attendance Import Flow

```text
.xlsx upload
  -> extension and size validation
  -> dynamic header/date detection
  -> row normalization
  -> percentage validation
  -> duplicate detection
  -> student matching within class scope
  -> attendance_records
  -> attendance_summaries
  -> import summary response
```

The parser accepts variable date columns and preserves the college-provided `Tot.(%)` value. Date-wise records are still stored for reporting and future analytics. A summary stores the percentage, date period, source type, and import batch.

The parser does not infer approved leave from arbitrary attendance markers. Leave semantics must be implemented explicitly after the college policy is confirmed.

## Campaign Eligibility

Campaign creation resolves the threshold from the request or `system_settings.attendance_threshold_default`. The threshold is copied into the campaign and every target.

Eligibility is:

```text
attendance_percentage < threshold_used
```

Each eligible student becomes a `campaign_targets` snapshot containing:

- attendance percentage used
- threshold used
- eligibility reason
- student ID
- selected parent ID
- selected phone number
- target status

Later changes to attendance, contacts, or configuration do not rewrite historical target snapshots.

## Calling Architecture

```text
campaign_target
  -> queue_campaign_target()
  -> CallAttempt(status=QUEUED)
  -> worker dispatch
  -> CallingProvider interface
  -> provider call events
```

The provider contract is in `app/integrations/calling/base.py`. Core campaign logic does not depend on Twilio, Exotel, Plivo, or another vendor. `dispatch_call()` requires an injected provider adapter and is not called directly from a normal request handler.

## Conversations and AI

A call can create one conversation. Transcript segments are stored with speaker, sequence number, text, and confidence. The database enforces unique `(conversation_id, sequence_number)` values.

`AIAnalyzer` returns an advisory `AnalysisResult`. The backend persists the result but does not allow AI output to execute calls or follow-ups directly. Business rules remain authoritative.

## Follow-ups

A callback request must include an explicit timezone-aware datetime. Follow-up states are separated:

```text
SCHEDULED -> DUE -> IN_PROGRESS -> COMPLETED
                         |
                         +-> CANCELLED
```

The worker marks only records whose `scheduled_for <= now` as `DUE`. A scheduled callback is never called immediately merely because an AI analysis requested one.

## Dashboard

`GET /api/v1/dashboard/summary` returns scope-filtered counts for students, eligible targets, campaigns, calls, and follow-ups. Every query applies the authenticated user scope unless the user is a super administrator.

## Migration Strategy

The original applied revision is preserved:

```text
668cfee1d9d3_initial_database_schema
```

Later revisions are additive and currently include:

- authorization tables
- class scopes
- attendance summaries
- campaign thresholds and targets
- campaign-target call links
- AI model versions and transcript uniqueness
- follow-up scheduling fields
- call/follow-up permissions
- reports permission

Never rewrite the initial migration. Review generated SQL and inspect the live revision before applying a new migration.

## Validation Commands

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m compileall -q app migrations
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\alembic.exe current
.\.venv\Scripts\alembic.exe heads
```

The active development environment uses Python 3.13.7 and `backend/.venv`.

## Current Limitations

- The Excel service currently supports `.xlsx`; `.xls` is not enabled.
- Import files are parsed in the request path; large-scale production deployment should enqueue imports.
- Provider adapters and real telecom credentials are intentionally not implemented.
- Follow-up worker execution needs a long-running worker or queue deployment.
- Leave policy, bulk student updates, reports with arbitrary filters, audit mutation hooks, and full integration fixtures remain to be implemented.
- The current test suite focuses on parser and rule behavior; database-backed authorization and workflow integration tests should be expanded before production use.

## Professor Explanation

- FastAPI provides typed HTTP contracts and dependency-based authentication.
- PostgreSQL provides relational integrity, foreign keys, indexes, and transactional state.
- SQLAlchemy separates database models from API schemas.
- Alembic makes schema evolution reproducible without rewriting applied history.
- Argon2 protects passwords, while JWT carries identity between requests.
- Permissions and scopes are enforced by the backend because frontend filtering is not security.
- Attendance snapshots and campaign targets preserve historical decisions.
- Provider adapters prevent telecom vendor changes from rewriting business logic.
- AI is advisory; backend rules remain authoritative.
- A scheduler is required because a requested callback is a future action, not an immediate call.

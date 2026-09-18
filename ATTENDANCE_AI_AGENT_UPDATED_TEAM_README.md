# Attendance AI Agent --- Updated Production Architecture & Team Integration README

**Project status:** Architecture baseline for team development\
**Purpose:** This README is the shared contract for Backend, Frontend,
Voice Agent, ML and Git/GitHub integration.

------------------------------------------------------------------------

## 1. Project Vision

Attendance AI Agent is a production-oriented college attendance
communication system.

The system receives attendance data from the college, maintains
student/academic/contact information, determines students eligible for
communication using a **configurable attendance threshold**, creates
call campaigns, calls parents/guardians through a provider-independent
calling layer, captures their response, converts the response to text,
analyzes the response, schedules follow-ups when required, and provides
dashboards/reports/audit history.

The architecture must support:

-   Multiple administrators for different academic scopes such as MBA
    and B.Tech.
-   Staff users with restricted permissions/scopes.
-   Individual and bulk student-data updates.
-   Attendance imports from Excel, CSV, PDF tables, and DOCX tables with variable numbers of date columns.
-   Attendance percentage as the primary campaign eligibility value.
-   Attendance dates retained because they are required for leave,
    reporting, scheduling and future analytics/ML.
-   Approved leave handling according to college policy.
-   Scheduled callbacks such as "call on Monday".
-   A future/custom in-house voice agent.
-   A future ML model for repeat-call prediction, timing recommendations
    and response classification.
-   Independent frontend/backend/agent/ML development with clean GitHub
    integration.
-   Addition of future features without rewriting the core system.

------------------------------------------------------------------------

# 2. Non-Negotiable Architecture Principles

### 2.1 Separation of concerns

Do not mix:

-   UI logic with database logic.
-   Calling-provider code with campaign business logic.
-   AI/ML predictions with authorization.
-   Excel parsing with frontend code.
-   Scheduled follow-up logic with a specific telecom provider.

Each layer communicates through defined contracts.

### 2.2 Backend is the source of truth

Frontend, Voice Agent and ML must not directly modify PostgreSQL.

All production data changes go through backend APIs/services.

``` text
Frontend
   |
   v
FastAPI API
   |
   v
Business Services
   |
   v
PostgreSQL
```

### 2.3 AI/ML does not bypass business rules

AI/ML may recommend:

-   response category
-   follow-up required
-   priority
-   suggested callback time
-   repeat-call probability

But the backend decides whether an action is actually allowed.

``` text
AI/ML Recommendation
        |
        v
Backend Validation + Business Rules
        |
        v
Allowed Action
```

### 2.4 Provider independence

Telecom, STT, TTS, LLM and Voice Agent providers must be isolated behind
interfaces/adapters.

A provider can be replaced without rewriting campaign/student/reporting
logic.

### 2.5 Historical data must not be casually overwritten

Academic history, campaign targets, attendance snapshots and important
audit events must remain traceable.

------------------------------------------------------------------------

# 3. High-Level Architecture

``` text
                         ┌──────────────────────┐
                         │      FRONTEND        │
                         │ Dashboard / Students │
                         │ Attendance / Reports │
                         └──────────┬───────────┘
                                    │ HTTPS/JSON
                                    ▼
                         ┌──────────────────────┐
                         │     FASTAPI CORE     │
                         │ Auth + RBAC + APIs   │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
       Student Service       Attendance Service      Campaign Service
              │                     │                     │
              ▼                     ▼                     ▼
       Academic/Contact       Excel Import +        Eligibility +
       Management             Attendance Data       Target Snapshot
                                    │                     │
                                    └──────────┬──────────┘
                                               ▼
                                      Follow-up Engine
                                               │
                               ┌───────────────┴──────────────┐
                               ▼                              ▼
                         Rule Engine                    ML Service
                               │                              │
                               └───────────────┬──────────────┘
                                               ▼
                                          Call Queue
                                               │
                                               ▼
                                       Calling Service
                                               │
                                     Voice Agent Interface
                                        /             \
                                       ▼               ▼
                              External Agent      Own Agent
                                                       │
                                                  STT / LLM / TTS
                                                       │
                                                       ▼
                                               Conversation Data
                                                       │
                                                       ▼
                                                 Transcript
                                                       │
                                                       ▼
                                                AI Analyzer
                                                       │
                                                       ▼
                                              Follow-up / Leave
```

------------------------------------------------------------------------

# 4. Team Ownership

## Backend Developer --- This repository/core

Responsible for:

-   FastAPI
-   PostgreSQL
-   SQLAlchemy
-   Alembic
-   authentication
-   RBAC
-   student management
-   academic history
-   contact management
-   bulk updates
-   attendance import
-   attendance snapshots
-   leave workflow APIs
-   campaign engine
-   follow-up engine
-   calling integration contracts
-   transcript/AI-analysis storage
-   reports APIs
-   audit logs
-   integration tests

Backend owns the database schema and public API contracts.

------------------------------------------------------------------------

## Frontend Developer

Responsible for:

-   Login
-   Dashboard
-   Student screens
-   Attendance/import screens
-   Campaign screens
-   Call/conversation screens
-   Follow-ups
-   Reports
-   User/RBAC screens
-   Settings
-   Audit UI
-   Loading/error/empty states
-   API integration

Frontend must consume documented backend APIs and must not directly
query PostgreSQL.

------------------------------------------------------------------------

## Voice Agent Developer

Responsible for:

-   Voice conversation flow
-   STT/TTS integration
-   Agent conversation logic
-   Calling-provider integration where applicable
-   Call events/webhooks
-   Transcript generation
-   Structured response extraction

The Voice Agent must communicate with the backend through the agreed
API/event contract.

It must not own student eligibility, authorization or campaign
decisions.

------------------------------------------------------------------------

## ML Developer

Responsible for:

-   Feature engineering
-   Training datasets
-   Model training
-   Evaluation
-   Prediction API/service
-   Model versioning
-   Monitoring
-   Retraining strategy

ML must provide predictions/recommendations through a stable API
contract.

ML does not directly update production business records.

------------------------------------------------------------------------

# 5. GitHub Repository Strategy

Two acceptable strategies:

### Recommended for this project

One GitHub repository with clear folders:

``` text
attendance-ai-agent/
│
├── backend/
├── frontend/
├── voice-agent/
├── ml/
├── docs/
├── .github/
├── README.md
└── .gitignore
```

This makes integration easier for a college team while keeping ownership
clear.

Alternative: separate repositories can be used if developers prefer, but
the API/event contracts must remain identical.

### Never commit

-   `.env`
-   passwords
-   JWT secrets
-   API keys
-   telecom credentials
-   database credentials
-   private certificates
-   generated private datasets

Use `.env.example`.

------------------------------------------------------------------------

# 6. Git Workflow

Do not directly push unfinished work to `main`.

Recommended:

``` text
main
  |
  ├── backend/student-module
  ├── backend/attendance-import
  ├── backend/rbac
  ├── frontend/dashboard
  ├── voice-agent/call-flow
  └── ml/repeat-call-model
```

Workflow:

``` text
git pull
        ↓
create feature branch
        ↓
develop + test
        ↓
commit
        ↓
push branch
        ↓
Pull Request
        ↓
review
        ↓
merge
```

### Commit style

Use readable commits:

``` text
feat: add student bulk update API
feat: add attendance import validation
feat: add role scope authorization
fix: prevent duplicate attendance import
feat: add campaign target snapshot
feat: add follow-up scheduling API
```

Avoid:

``` text
final
final2
new
working
changes
```

------------------------------------------------------------------------

# 7. Backend Folder Architecture

Recommended structure:

``` text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── routes/
│   │       └── router.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── jwt.py
│   │
│   ├── db/
│   │   └── session.py
│   │
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── integrations/
│   │   ├── telecom/
│   │   ├── voice_agent/
│   │   └── ml/
│   ├── workers/
│   └── main.py
│
├── migrations/
├── tests/
├── requirements.txt
└── .env.example
```

### Rule

`routes` receive HTTP requests.

`schemas` validate request/response data.

`services` contain business logic.

`models` represent database structure.

`integrations` contain external-provider adapters.

`workers` handle background/scheduled jobs.

------------------------------------------------------------------------

# 8. Authentication & Authorization

Authentication:

``` text
Login
 ↓
JWT
 ↓
Current User
```

Authorization:

``` text
Current User
     ↓
Role
     +
Permissions
     +
Scope
     ↓
Allowed / Denied
```

## Roles

Suggested baseline:

-   `SUPER_ADMIN`
-   `ADMIN`
-   `STAFF`
-   `VIEWER`

Exact role names can change, but the architecture must support role
expansion.

## Permissions

Examples:

``` text
student.read
student.create
student.update
student.bulk_update

attendance.read
attendance.import

leave.read
leave.create
leave.approve

campaign.read
campaign.create
campaign.start
campaign.pause

calls.read
calls.manage

followup.read
followup.manage

reports.read
reports.export

user.manage
role.manage
settings.manage
audit.read
```

## Scope

A user may be restricted to:

-   College
-   Department
-   Course
-   Branch
-   Section/Class

Example:

``` text
User: MBA Admin
Role: ADMIN
Scope: MBA

User: B.Tech Admin
Role: ADMIN
Scope: B.Tech
```

A B.Tech Admin must not receive MBA records from backend APIs unless
explicitly authorized.

------------------------------------------------------------------------

# 9. Student Data Architecture

## Student master

Stable/basic information:

``` text
student_id
name
student_mobile
father_name
father_mobile
alternative_contact_number
status
```

## Academic history

Separate entity:

``` text
student_academic_records

student_id
session
course
branch
section
year
semester
active/current
effective dates if required
```

The same student can have:

``` text
2024-25 → B.Tech → CSE → Year 1
2025-26 → B.Tech → CSE → Year 2
2026-27 → B.Tech → CSE → Year 3
```

Do not destroy previous records just because the current academic
details changed.

------------------------------------------------------------------------

# 10. Parent/Guardian Contacts

A student may have:

-   father
-   mother
-   guardian
-   alternate contact

The data model should support multiple contacts.

Important fields can include:

``` text
student_id
contact/person id
relationship
phone
is_primary
is_active
```

If a phone number changes:

``` text
Admin/authorized staff
        ↓
Update contact
        ↓
Validation
        ↓
Audit
```

Do not make the phone number the student's identity.

------------------------------------------------------------------------

# 11. Individual & Bulk Student Updates

### Individual update

Search → open student → edit → validate → save → audit.

### Bulk update

``` text
Filter
 ↓
Select students
 ↓
Choose fields to change
 ↓
Enter new value
 ↓
Preview affected count
 ↓
Confirm
 ↓
Transaction
 ↓
Audit summary
```

Blank fields mean:

> Keep current value.

Never silently overwrite unrelated fields.

------------------------------------------------------------------------

# 12. Attendance File Import

The college attendance file currently appears to contain:

``` text
S.No
Roll No / Student ID
Name
Multiple attendance-date columns
P
A
Tot.
Tot.(%)
NF
```

The exact column names must be detected from the actual production file
when available.

Supported upload formats are `.xlsx`, `.xls`, `.csv`, `.pdf` tables, and
`.docx` tables. Legacy binary `.doc` files are not supported. The backend
normalizes each supported table format before applying the same validation
and student-matching rules.

## Important

The number of date columns is variable.

Do not hard-code:

``` text
21 dates
15 dates
20 dates
```

Instead:

``` text
Detect header/date columns dynamically
```

## Campaign eligibility

`Tot.(%)` is the primary attendance percentage source when supplied by
the college.

Example:

``` text
72.22%
81.25%
66.67%
```

The campaign engine uses the percentage, not individual P/A cells, to
decide basic eligibility.

## Dates are still retained

Dates are useful for:

-   attendance period
-   leave
-   reports
-   callbacks
-   follow-ups
-   trend analysis
-   ML features

Therefore:

> Do not delete date information merely because campaign eligibility
> does not directly use it.

------------------------------------------------------------------------

# 13. Attendance Threshold

Never hard-code `75%`.

Threshold is configuration/business data.

Example:

``` text
attendance_threshold = 75
```

Admin may configure:

``` text
70%
75%
80%
85%
```

Campaign creation can use the applicable configured threshold.

Eligibility:

``` text
attendance_percentage < threshold
        ↓
eligible
```

The comparison operator and exact college policy must be finalized with
faculty.

------------------------------------------------------------------------

# 14. Attendance Snapshot

When an Excel is imported, preserve the attendance value used at that
time.

Conceptually:

``` text
attendance_snapshot

id
student_id
attendance_percentage
attendance_period
source_import_id
recorded_at
```

This prevents historical campaign results from changing when a newer
attendance file is imported.

Example:

``` text
Import A → 72%
Campaign A → used 72%

Later:
Import B → 68%
Campaign B → used 68%
```

------------------------------------------------------------------------

# 15. Leave Management

Leave must be a separate business entity, not simply another spelling of
ABSENT.

Concept:

``` text
student_leaves

id
student_id
start_date
end_date
reason
status
requested_by
approved_by
approved_at
created_at
updated_at
```

Suggested statuses:

``` text
PENDING
APPROVED
REJECTED
CANCELLED
```

Dashboard:

``` text
Students on Leave
```

### Percentage rule

The system must apply the college's official approved-leave attendance
policy.

Do not invent a percentage adjustment rule.

If the college says approved leave should not affect attendance, the
calculation/import logic must follow that policy.

------------------------------------------------------------------------

# 16. Campaign Architecture

Campaign creation should capture:

``` text
name
attendance period
academic scope
threshold
eligible student count
created_by
status
```

Before campaign creation/start:

``` text
Attendance %
      ↓
Threshold
      ↓
Eligible population
      ↓
Contact validation
      ↓
Preview
      ↓
Confirm
```

## Campaign target snapshot

When a campaign is created, freeze its target context.

Concept:

``` text
campaign_targets

campaign_id
student_id
parent/contact_id
attendance_percentage_used
eligibility_reason
status
```

This makes historical campaigns reproducible.

------------------------------------------------------------------------

# 17. Calling Architecture

Never write:

``` text
Campaign Service → Provider API directly everywhere
```

Use:

``` text
Campaign Service
      ↓
Calling Service
      ↓
Telecom Adapter
      ↓
Provider
```

Voice:

``` text
Calling Service
      ↓
Voice Agent Interface
      ↓
External Voice Agent
```

Future:

``` text
Calling Service
      ↓
Voice Agent Interface
      ↓
Own Voice Agent
```

This allows provider replacement without changing campaign logic.

------------------------------------------------------------------------

# 18. Voice Agent Contract

The Voice Agent should receive only the information it needs.

Example conceptual request:

``` json
{
  "call_id": "uuid",
  "student_id": "24BTCS0039",
  "student_name": "Student Name",
  "contact_id": "uuid",
  "purpose": "attendance_followup",
  "attendance_percentage": 68.5,
  "language": "en"
}
```

The actual production contract should minimize personal data and be
finalized before integration.

Voice Agent returns structured events/results such as:

``` json
{
  "call_id": "uuid",
  "status": "COMPLETED",
  "transcript_id": "uuid",
  "response_category": "CALLBACK_REQUESTED",
  "followup_required": true
}
```

Do not make the Voice Agent responsible for database authorization.

------------------------------------------------------------------------

# 19. Parent Response Processing

Flow:

``` text
Call
 ↓
Audio
 ↓
STT
 ↓
Transcript
 ↓
Response Analyzer
 ↓
Structured Response
 ↓
Backend Rules
 ↓
Action
```

Possible categories:

``` text
WILL_ATTEND
WILL_NOT_ATTEND
CALLBACK_REQUESTED
MEDICAL_REASON
LEAVE_RELATED
NO_RESPONSE
WRONG_NUMBER
OTHER
```

The list is extensible.

Do not make the database depend on a fixed small list forever. Use
stable categories plus an extensible metadata field where appropriate.

------------------------------------------------------------------------

# 20. Scheduled Follow-ups

Example:

Parent says:

> "Monday ko call karna."

System should create:

``` text
followup
scheduled_for = Monday
status = SCHEDULED
reason = CALLBACK_REQUESTED
```

Scheduler:

``` text
Before Monday
    ↓
Do not call

Monday
    ↓
Due
    ↓
Queue
    ↓
Call
```

The AI cannot bypass this rule.

Support:

-   date
-   time/window
-   timezone
-   reason
-   assigned staff
-   status
-   retry count
-   cancellation

------------------------------------------------------------------------

# 21. Rule Engine + ML Engine

Use two separate concepts.

## Rule Engine

Deterministic rules:

``` text
attendance < threshold
contact valid
not excluded
not before callback date
campaign active
```

## ML Engine

Predictive recommendations:

``` text
repeat_call_probability
followup_priority
suggested_followup_time
response_classification
```

Architecture:

``` text
Business Data
     ↓
Rule Engine
     ↓
ML Recommendation (optional)
     ↓
Backend validation
     ↓
Final action
```

ML should not directly execute calls.

------------------------------------------------------------------------

# 22. ML Integration Contract

ML should ideally expose a versioned API/service.

Example:

``` text
POST /predict/repeat-call
```

Input:

``` json
{
  "student_id": "uuid",
  "attendance_percentage": 68.5,
  "previous_call_count": 2,
  "previous_unanswered_count": 1,
  "days_since_last_call": 4,
  "last_response_category": "CALLBACK_REQUESTED"
}
```

Output:

``` json
{
  "model_version": "v1",
  "repeat_call_score": 0.81,
  "recommended_priority": "HIGH",
  "recommended_followup": true
}
```

The backend decides whether this recommendation is actionable.

Never allow the ML service to receive unnecessary personal data.

------------------------------------------------------------------------

# 23. Reports & Filters

Reports must support filtering.

Suggested filters:

``` text
Session
Course
Branch
Section
Year
Semester
Student ID
Student Name

Attendance %
Attendance Period
Attendance Date

Campaign
Campaign Status
Call Status

Response Category
Follow-up Status
Follow-up Date

Leave Status
```

Examples:

-   Students below configured threshold.
-   Students currently on approved leave.
-   Calls due today.
-   Calls scheduled after a parent request.
-   Unanswered calls.
-   Follow-ups pending.
-   Campaign performance by academic scope.

------------------------------------------------------------------------

# 24. Dashboard

Dashboard should show:

``` text
Total Students
Eligible Students
Students on Leave
Active Campaigns
Completed Calls
Failed Calls
Unanswered Calls
Follow-ups Due
Scheduled Follow-ups
```

Also:

### Recent Activity

Examples:

``` text
Attendance import completed
Student contact updated
Leave approved
Campaign created
Campaign completed
Follow-up scheduled
```

### Current Scope

Always show the logged-in user's active data scope.

Example:

``` text
B.Tech / CSE
```

This reduces accidental work on the wrong department.

------------------------------------------------------------------------

# 25. UI Page List

## Authentication

1.  Login
2.  Profile

## Main

3.  Dashboard
4.  Notifications

## Student

5.  Student List
6.  Student Details
7.  Add Student
8.  Edit Student
9.  Bulk Update
10. Academic History
11. Parent/Guardian Contacts

## Attendance

12. Attendance Overview
13. Excel Import
14. Import Preview
15. Import Details
16. Attendance History

## Leave

17. Leave List
18. Leave Details
19. Leave Approval

## Campaign

20. Campaign List
21. Create Campaign
22. Campaign Details
23. Campaign Target List

## Calling

24. Call Queue
25. Call Details
26. Conversations
27. Transcript
28. Follow-ups

## Reports

29. Reports Dashboard
30. Attendance Report
31. Campaign Report
32. Call Report
33. Follow-up Report

## Administration

34. Users
35. Roles & Permissions
36. Scope Management
37. Settings
38. Audit Logs

------------------------------------------------------------------------

# 26. Frontend/Backend API Contract Rules

Backend API responses should be stable and documented through OpenAPI.

Frontend should not depend on:

-   SQL column names that are not part of the API contract.
-   Internal Python class names.
-   Internal database IDs unless returned intentionally.
-   Provider-specific response formats.

If an API changes:

1.  Update schema.
2.  Update OpenAPI.
3.  Notify frontend.
4.  Update integration tests.
5.  Prefer backward-compatible changes where possible.

------------------------------------------------------------------------

# 27. API Versioning

Current:

``` text
/api/v1/...
```

Do not silently break existing frontend integration.

For breaking changes:

``` text
/api/v2/...
```

or introduce a documented migration strategy.

------------------------------------------------------------------------

# 28. Error Response Standard

Use predictable errors.

Example:

``` json
{
  "detail": "Student ID already exists"
}
```

For validation:

``` json
{
  "detail": [
    {
      "field": "attendance_percentage",
      "message": "Value must be between 0 and 100"
    }
  ]
}
```

Frontend should display user-friendly messages.

Never expose stack traces, passwords, secrets or database credentials.

------------------------------------------------------------------------

# 29. Background Jobs

The following should not block normal HTTP requests when they become
long-running:

-   large Excel processing
-   campaign queue preparation
-   scheduled follow-ups
-   call status synchronization
-   transcript processing
-   ML prediction batches
-   report generation for large datasets

Use a worker/job system when required.

The exact technology can be selected later; business services must
remain independent of the worker implementation.

------------------------------------------------------------------------

# 30. Adding New Features Safely

When someone proposes a feature:

``` text
Requirement
    ↓
Business rule
    ↓
Data impact
    ↓
API impact
    ↓
UI impact
    ↓
AI/ML impact
    ↓
Migration
    ↓
Tests
    ↓
Implementation
```

Example new feature:

> "Send notification when follow-up is overdue."

Do not put notification code inside every existing service.

Instead:

``` text
Follow-up status
      ↓
Event / service action
      ↓
Notification Service
      ↓
Email/SMS/In-app adapter
```

This keeps future features modular.

------------------------------------------------------------------------

# 31. Events for Future Extensibility

Where useful, use internal domain events such as:

``` text
STUDENT_UPDATED
ATTENDANCE_IMPORTED
LEAVE_APPROVED
CAMPAIGN_CREATED
CAMPAIGN_STARTED
CALL_COMPLETED
TRANSCRIPT_CREATED
RESPONSE_ANALYZED
FOLLOWUP_CREATED
FOLLOWUP_DUE
```

A future notification, analytics or ML service can subscribe without
rewriting the original feature.

Do not introduce a complex event-bus infrastructure prematurely. Start
with clean service boundaries and add asynchronous events when
scale/requirements justify it.

------------------------------------------------------------------------

# 32. Security Rules

Mandatory:

-   Password hashing.
-   JWT validation.
-   Role + permission + scope checks.
-   HTTPS in production.
-   Secrets in environment/configuration management.
-   Audit sensitive actions.
-   Database least-privilege user.
-   Input validation.
-   File-upload validation.
-   File size/type limits.
-   No sensitive information in logs.
-   No direct frontend database access.
-   No hard-coded provider keys.
-   Rate limiting where appropriate.
-   Backup and restore plan.

------------------------------------------------------------------------

# 33. Attendance Import Safety

Import must have:

``` text
Upload
 ↓
Validate
 ↓
Preview
 ↓
Commit
```

Validation should detect:

-   missing Student ID
-   duplicate Student ID
-   unknown Student ID
-   missing percentage
-   percentage outside 0--100
-   malformed data
-   unsupported file format
-   unexpected headers
-   duplicate import where policy forbids it

Invalid rows should be reported, not silently ignored.

------------------------------------------------------------------------

# 34. Testing Strategy

## Backend

Test:

-   authentication
-   role authorization
-   scope authorization
-   student CRUD
-   bulk updates
-   academic history
-   parent/contact changes
        -   Attendance file validation for Excel, CSV, PDF, and DOCX inputs
-   attendance percentage
-   threshold changes
-   leave approval
-   campaign target snapshot
-   callback scheduling
-   duplicate protection
-   audit logs

## Frontend

Test:

-   login
-   permission-based UI
-   filters
-   bulk update
-   import states
-   campaign workflow
-   follow-up workflow
-   error states

## Voice Agent

Test:

-   call initiation
-   successful conversation
-   no answer
-   failed call
-   transcript
-   response extraction
-   callback request
-   wrong number
-   provider failure

## ML

Test:

-   schema validation
-   model version
-   prediction range
-   missing features
-   model failure fallback
-   drift/monitoring plan

------------------------------------------------------------------------

# 35. Failure Handling

External services can fail.

Example:

``` text
Voice Provider Down
       ↓
Call attempt = FAILED
       ↓
Failure reason recorded
       ↓
Retry policy
       ↓
Queue again OR manual review
```

ML service unavailable:

``` text
ML unavailable
      ↓
Use deterministic business rules
      ↓
Continue system operation
```

This means ML is an enhancement, not a single point of failure.

------------------------------------------------------------------------

# 36. Data Ownership

  Data                   Owner
  ---------------------- -----------------------
  Student master         Backend/Admin
  Academic history       Backend/Admin
  Parent contacts        Backend/Admin
  Attendance imports     Backend
  Attendance snapshots   Backend
  Campaigns              Backend
  Call events            Calling/Backend
  Transcripts            Voice Agent + Backend
  AI analysis            AI/Backend
  ML predictions         ML
  UI state               Frontend

------------------------------------------------------------------------

# 37. Integration Contract Between Developers

### Frontend → Backend

Use:

``` text
HTTPS
JSON
JWT
OpenAPI
```

### Voice Agent → Backend

Use:

``` text
Authenticated API/webhook
Stable event/request schemas
Idempotent call-event handling
```

### Backend → ML

Use:

``` text
Versioned API
Structured JSON
Model version in response
Timeout/fallback
```

### Database

Only backend owns schema migrations.

Frontend/Voice/ML developers must not create independent production
tables without backend architecture review.

------------------------------------------------------------------------

# 38. Idempotency

Important for webhooks and retries.

If a provider sends the same event twice:

``` text
CALL_COMPLETED
CALL_COMPLETED
```

the backend must not create duplicate business records.

Use a provider event ID / idempotency key where available.

------------------------------------------------------------------------

# 39. Time & Scheduling

Store timestamps in a consistent timezone-aware format.

Scheduling must account for:

-   date
-   time
-   timezone
-   permitted calling window
-   holiday/college schedule if required later
-   parent-requested callback date
-   campaign schedule

Do not call before a user-requested callback date.

------------------------------------------------------------------------

# 40. Production Database Direction

Core entities:

``` text
users
roles
permissions
role_permissions
user_scopes

students
student_academic_records

parents / contacts
student_parent_links

attendance_import_batches
attendance_records / attendance_snapshots

leave_requests / student_leaves

call_campaigns
campaign_targets
call_attempts

conversations
transcripts
ai_analyses

followups
audit_logs
system_settings
```

Exact table names may differ from the current implementation. The
separation of responsibilities is the important contract.

------------------------------------------------------------------------

# 41. Current Existing Backend Context

The current backend already has the foundational modules for:

-   users
-   classes
-   students
-   parents
-   student-parent links
-   attendance imports
-   attendance records
-   absence events
-   campaigns
-   call attempts
-   conversations
-   transcripts
-   AI analysis
-   follow-ups
-   audit logs
-   system settings

Because the faculty requirements have changed, the existing model
structure should be reviewed before adding major campaign/import
functionality.

Do not create duplicate tables just because a new requirement appeared.
First inspect existing migrations/models and decide whether to modify,
extend or replace a structure.

------------------------------------------------------------------------

# 42. Current Development Priority

Before continuing large-scale campaign implementation:

### Phase 1 --- Architecture lock

-   Multi-admin RBAC
-   Scope model
-   Student/basic data
-   Academic history
-   Parent/contact model
-   Attendance snapshot strategy
-   Date/attendance handling
-   Leave model
-   Bulk update rules
-   Campaign snapshot

### Phase 2 --- Actual Excel contract

When college Excel is available:

-   inspect actual headers
-   detect date columns
-   confirm Student ID column
-   confirm percentage column
-   confirm meaning of P/A/Tot./NF
-   confirm leave representation
-   implement parser
-   validation tests

### Phase 3 --- Backend

-   migrations
-   models
-   schemas
-   services
-   APIs
-   permissions
-   tests

### Phase 4 --- Frontend

Build against stable APIs.

### Phase 5 --- Voice Agent

Integrate through the calling/voice-agent contract.

### Phase 6 --- ML

Integrate prediction service after enough usable historical data exists.

### Phase 7 --- Production testing/deployment

-   security testing
-   load testing
-   failure testing
-   database backup/restore
-   monitoring
-   deployment

------------------------------------------------------------------------

# 43. Important Rule About ML

The first version may not have enough historical data for a reliable ML
model.

Do not invent training data.

Start by collecting structured historical outcomes:

``` text
call outcome
response category
follow-up result
days to resolution
retry count
callback result
attendance percentage
leave status
```

Once sufficient real data exists, the ML developer can train/evaluate a
model.

Until then:

``` text
Rule Engine = primary
ML = optional recommendation
```

------------------------------------------------------------------------

# 44. Important Rule About Voice Agent

The first Voice Agent can be external or simple.

But the core system must not depend on a specific provider.

The interface should remain stable:

``` text
start_call()
handle_call_event()
get_transcript()
end_call()
```

Actual implementation can change.

Future:

``` text
Provider A → Provider B → Own Voice Agent
```

without rewriting campaign/student modules.

------------------------------------------------------------------------

# 45. UI Design Principles

The UI should feel like a premium modern college operations dashboard,
not a generic admin template.

Requirements:

-   consistent design system
-   3D/soft-depth visual language where appropriate
-   clear cards
-   readable tables
-   strong filtering
-   responsive layout
-   accessible contrast
-   confirmation dialogs for bulk/high-impact actions
-   clear status badges
-   loading skeletons
-   empty states
-   error states
-   permission-denied states
-   success notifications
-   import progress
-   campaign progress

Do not sacrifice usability for visual effects.

------------------------------------------------------------------------

# 46. UI Developer Must Know

Frontend must not decide:

``` text
Is this student eligible?
Can this user edit this student?
Can this campaign start?
Can this user see MBA data?
```

Frontend may display the state returned by backend.

Backend decides.

------------------------------------------------------------------------

# 47. Final Architecture Rule

The project should be designed as a **platform**, not as one giant
feature.

Future features such as:

-   SMS notifications
-   WhatsApp integration
-   email alerts
-   parent portal
-   mobile app
-   predictive attendance
-   risk scoring
-   additional AI agents
-   automated reports
-   notification engine
-   college timetable integration

should be addable through new modules/services/adapters without
rewriting existing core logic.

------------------------------------------------------------------------

# 48. Definition of Done

A feature is not complete when the code "works on one machine."

It is complete when:

-   requirement is documented
-   API/schema is defined
-   authorization is implemented
-   database migration exists if needed
-   service logic is tested
-   error handling exists
-   frontend integration is possible
-   audit requirements are considered
-   logs are safe
-   documentation is updated
-   Git branch/PR is reviewed
-   regression tests pass

------------------------------------------------------------------------

# 49. Team Communication Rule

When changing an API/model:

``` text
Developer
   ↓
Update contract/documentation
   ↓
Tell affected developers
   ↓
Implement
   ↓
Test
   ↓
PR
```

Never make a breaking change silently.

------------------------------------------------------------------------

# 50. Final One-Line System Flow

``` text
Student Data + Academic History
        +
Attendance File (Excel / CSV / PDF / DOCX)
        ↓
Validation + Attendance Snapshot
        ↓
Configurable Threshold
        ↓
Campaign Target Snapshot
        ↓
Calling Service
        ↓
Voice Agent
        ↓
Parent Response + Transcript
        ↓
AI Response Analysis
        ↓
Rule Engine + Optional ML Recommendation
        ↓
Follow-up / Leave / Retry / No Further Action
        ↓
Dashboard + Reports + Audit
```

------------------------------------------------------------------------

## Team Agreement

**This README is the shared architecture baseline.**

Before adding a major feature, ask:

1.  Does it belong in the correct layer?
2.  Does it require a database change?
3.  Does it change an API contract?
4.  Does it affect permissions/scope?
5.  Does the frontend need a new screen/state?
6.  Does Voice Agent or ML need a new contract?
7.  Can it be added without tightly coupling existing modules?
8.  What tests prove it works?

If the answer is clear, implement it through the appropriate module
instead of adding logic to an unrelated service.

**Goal: production-quality, modular, testable, provider-independent and
easy to extend.**

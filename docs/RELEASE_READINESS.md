# Release Readiness

This is the remaining work based on the code and documentation currently in
the repository. Items involving real calling, student data, or model
predictions require institutional approval and real deployment decisions;
they cannot be completed safely from source code alone.

## Must complete before an end-to-end pilot

- [x] **Connect the core frontend workflows to the backend.** Sign-in,
  dashboard summary, class/student reads and creation, attendance import,
  and campaign creation use the API and handle common loading/error states.
- [ ] Add frontend screens for remaining backend workflows and browser
  end-to-end tests. Continue verifying that role and academic-scope
  restrictions come from backend enforcement.
- [ ] **Connect backend campaigns to the voice service.** Implement the
  backend-side provider/dispatch integration, queue and retry policy,
  idempotency mapping, status callbacks, and call/conversation persistence.
  Keep it disabled until the backend can prove explicit guardian-contact
  authorization for each target.
- [ ] **Validate PostgreSQL end to end.** Apply all migrations to a fresh,
  disposable database; test startup, authentication, scoped reads/writes,
  attendance import, campaign creation, follow-up transitions, and upgrade
  from the previously deployed revision. Confirm backups and rollback
  procedures.
- [ ] **Settle privacy and calling policy.** Obtain school/legal approval for
  consent, calling hours, opt-outs, AI-provider processing, data residency,
  retention/deletion, and incident response. Test guardian verification,
  wrong-number handling, refusal, interruption, and low-confidence paths.
- [ ] **Review live provider operation.** Validate webhook signature checks,
  TLS/WSS, public URL reachability, API authentication, rate limiting,
  call-duration limits, retries, cost controls, and provider outage behavior.
  Pilot only with authorized test contacts and explicit human oversight.

## Must complete before claiming ML predictions

- [ ] Implement a runnable, versioned ML HTTP service and model-loading
  lifecycle.
- [ ] Establish lawful, representative labeled data and document target
  definitions, feature provenance, leakage prevention, bias evaluation, and
  data retention.
- [ ] Train and validate models against simple baselines; define metrics and
  acceptance thresholds before deployment. Calibrate probabilities and
  document uncertainty and unsupported inputs.
- [ ] Add automated tests, artifact/version compatibility checks, monitoring,
  drift detection, rollback, and human review. Keep predictions advisory.

## Must complete before public deployment

- [x] Add CI for PostgreSQL migrations, backend tests/syntax checks,
  voice-agent tests, and frontend lint/build on clean environments.
- [x] Add a Docker Compose starting point, health/readiness checks,
  environment examples, and service startup documentation.
- [ ] Harden and validate production deployment configuration, including a
  TLS domain/reverse proxy, database backup/restore, scaling and rollback.
- [ ] Complete production security and privacy review, including auth/session
  expiry, authorization boundaries, upload limits/content validation,
  dependency updates, audit events, secret storage/rotation, and access
  logging.
- [ ] Add observability: structured logs without sensitive personal data,
  error reporting, service/provider metrics, alerts, and an operator runbook.
- [ ] Add end-to-end and browser tests for the actual deployed
  frontend/backend/voice contracts; document supported browsers and
  accessibility checks.

## Current local validation

The checked-in commands are documented in the root README and
[`PROJECT_GUIDE.md`](PROJECT_GUIDE.md). Passing unit tests or a frontend
build is a local code-quality signal, not proof that provider credentials,
database integration, consent, production deployment, or complete product
workflows are ready.

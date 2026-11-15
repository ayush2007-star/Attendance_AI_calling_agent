CREATE TABLE IF NOT EXISTS voice_call_sessions (
    session_id UUID PRIMARY KEY,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    stream_token VARCHAR(128),
    call_sid VARCHAR(64) UNIQUE,
    context_json JSONB,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS parent_call_responses (
    session_id UUID PRIMARY KEY,
    student_id UUID NOT NULL,
    student_name VARCHAR(120) NOT NULL,
    response_text TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_parent_call_responses_student_id
    ON parent_call_responses (student_id);

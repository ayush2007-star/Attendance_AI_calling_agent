-- Optional migration for extended analytics columns in parent_call_responses
-- Run this with table-owner credentials:
-- psql "$DATABASE_URL" -f .\migrations\002_add_analytics_columns.sql

ALTER TABLE parent_call_responses
    ADD COLUMN IF NOT EXISTS response_category VARCHAR(64),
    ADD COLUMN IF NOT EXISTS followup_required BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS callback_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS transcript TEXT;

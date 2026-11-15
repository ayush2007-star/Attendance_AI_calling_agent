# Twilio attendance voice service

This is the voice-agent phone-call service. The main backend's campaign
dispatch still uses its local calling provider; wire it to this service only
after the backend can supply verified parent-contact authorization.

## Architecture

1. An authenticated backend caller submits one approved call context to
   `POST /calls`, with a unique `Idempotency-Key`.
2. The service creates a single Twilio outbound call. Twilio validates signed
   webhooks, then opens a bidirectional Media Stream over WSS.
3. Inbound 8 kHz G.711 μ-law frames go to Deepgram Nova-3 multilingual
   streaming STT (`language=multi`) and final Hindi/Hinglish text is handled
   by the call state machine.
4. Groq checks that the speaker explicitly confirms being the guardian before
   any student information is disclosed. Unclear answers fail closed.
5. After confirmation, a concise Groq response acknowledges the parent's
   reason. Cartesia streams Hindi/Hinglish speech back to Twilio in the same
   μ-law format. The parent's final reason is saved in PostgreSQL; call audio
   is not stored.

Twilio audio uses 8 kHz μ-law. The STT and TTS adapters normalize provider
details in `app/telephony/providers.py`; LLM requests use Groq's
OpenAI-compatible API endpoint and require a Groq API key, not an OpenAI key.
Changing model names, compatible base URLs, or credentials is
configuration-only. A different vendor's protocol needs an adapter
implementation, but should not require changing the call state machine.
Groq deprecated `llama-3.1-8b-instant` on August 16, 2026, so this service
defaults to its documented replacement, `openai/gpt-oss-20b`. Set `GROQ_MODEL`
to another currently active model only after checking Groq's model catalog
and testing Hindi/Hinglish response quality.

## Setup

From `voice-agent/`:

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
pip install -r requirements-telephony.txt
```

To make the one-request Cartesia WAV sample (no Cartesia SDK required), set a
fresh `CARTESIA_API_KEY` in `.env`, then run:

```powershell
python -m app.telephony.cartesia_tts_http --output output.wav
```

This sends one POST to Cartesia's `/tts/bytes` endpoint and writes the raw WAV
response bytes directly to the selected file. It is a standalone WAV sample;
the live Twilio stream continues to use the call service's μ-law 8 kHz TTS
adapter.

Set the provider keys, PostgreSQL `DATABASE_URL`, and Twilio account values in
`.env`. The database URL should point to a PostgreSQL database and use the
`postgresql+psycopg://user:password@host:5432/database` form. Select a Cartesia
multilingual voice that supports Hindi and English, then set its ID in
`CARTESIA_VOICE_ID`. Expose the service through a public HTTPS/WSS endpoint
and set `PUBLIC_BASE_URL` to that origin. Twilio uses this URL for
`/twiml/{session_id}`, `/status`, and `/media-stream`. Deepgram Aura does not
currently list Hindi among its supported TTS languages, so Cartesia is used
for Hindi/Hinglish speech.

The default Edge Hindi voice is `hi-IN-MadhurNeural` at `+25%` speed.
Adjust `EDGE_VOICE_RATE` in `.env` and restart the service to apply a different
rate.

Apply the schema migration once before starting the service:

```powershell
psql "$env:POSTGRES_MIGRATION_URL" -f .\migrations\001_create_voice_call_tables.sql
```

`POSTGRES_MIGRATION_URL` should point to the same database as `DATABASE_URL`.
The service checks for the migrated tables at startup and does not create
tables using its runtime database credentials.

The service refuses to originate calls unless both switches are explicitly
enabled:

```dotenv
REAL_CALLS_ENABLED=true
EXTERNAL_AI_PROCESSING_APPROVED=true
```

Keep them false for local tests. The call endpoint also requires a private
`X-API-Key`, an `Idempotency-Key`, and an explicit
`parent_contact_authorized: true` assertion in its request body. Do not expose
this service directly to the public internet without TLS, network controls,
and secrets management.

Run the API:

```powershell
# From voice-agent/:
.\.venv\Scripts\python.exe -m app.main
```

This starts the API on `http://127.0.0.1:8001`; starting the server alone does
not place a call. The service loads its `.env` relative to the `voice-agent`
directory.

Example request shape (use a real, authorized call context only after review):

```json
{
  "context": {
    "campaign_target_id": "00000000-0000-0000-0000-000000000001",
    "student_id": "00000000-0000-0000-0000-000000000002",
    "student_name": "Student Name",
    "parent_name": "Guardian Name",
    "phone_number": "<your-authorized-number-in-E.164>",
    "attendance_date": "2026-11-04",
    "preferred_language": "hi-IN"
  },
  "parent_contact_authorized": true
}
```

Send the request with `X-API-Key` and a new `Idempotency-Key` header. The
phone number must be E.164 formatted. Use only a number whose contact is
authorized.

The CLI below submits the same authenticated request to the service, which
creates the call using the Twilio Python client. Set a non-empty `CALL_API_KEY`
in `.env` (the same value used by the service) and explicitly confirm contact
authorization:

```powershell
$env:CALL_API_KEY="the-call-api-key-configured-on-the-service"; voice-agent\.venv\Scripts\python.exe voice-agent\app\telephony\trigger_call.py --campaign-target-id 00000000-0000-0000-0000-000000000001 --student-id 00000000-0000-0000-0000-000000000002 --student-name "Test Student" --parent-name "Test Guardian" --phone-number +919876543210 --attendance-date 2026-11-04 --idempotency-key internal-call-00000001 --parent-contact-authorized
```

Replace the example IDs, names, and number with the authorized call context.
Reuse the same idempotency key if retrying a request.
The service's `PUBLIC_BASE_URL` must be the public HTTPS origin reachable by
Twilio (for example, the HTTPS URL provided by ngrok); the service builds the
TwiML callback and WSS Media Stream URL from it.

Read stored responses by student from PostgreSQL:

```sql
SELECT student_name, response_text, recorded_at
FROM parent_call_responses
WHERE student_id = '00000000-0000-0000-0000-000000000002'
ORDER BY recorded_at DESC;
```

## Privacy and rollout notes

- The call first asks whether the named guardian is speaking. The attendance
  detail is only disclosed after the Groq verifier confirms this; uncertainty
  ends the call without disclosure.
- The bot says it will note the reason for school review. It does not claim
  leave has been marked or approved.
- Call context and the response are stored in PostgreSQL. Restrict database
  access; abandoned call context and stream tokens are cleared after one hour.
  Define a separate retention/deletion policy for saved responses.
- Provider API pricing, Twilio destination rates, call duration, taxes, and
  registration requirements vary. ₹1.50 per call is not guaranteed; measure
  end-to-end bills on short pilot calls before rollout.
- Hindi quality depends on the selected Cartesia voice. Deepgram Aura is not
  selected here because its published language list does not include Hindi.
- Check applicable Indian telecom, consent, privacy, and school policies with
  the institution and providers before calling real families.

# AttendWise AI — Final Submission & College Demonstration Checklist

**Project Title:** AI-Based Automated Student Absence Notification and Parent Response Management System (AttendWise AI)  
**Institution:** BBS College of Engineering and Technology (Department of Computer Science & Engineering)  
**Evaluation Date:** Academic Year 2026 Submission  

---

## 1. What Was Repaired & Completed

1. **Backend & Voice Agent Integration:**
   - Replaced dummy local calling stub with bidirectional server-to-server integration between the FastAPI backend (`port 8000`) and the telephony voice agent (`port 8001`).
   - Implemented `VoiceAgentCallingProvider` and `MockCallingProvider` in `app/integrations/calling/`.
   - Built authenticated webhook endpoint `/api/v1/calls/callback` to synchronize call duration, multi-turn transcripts, Groq response classification, and follow-ups directly into PostgreSQL entities (`CallAttempt`, `Conversation`, `Transcript`, `AIAnalysis`, `Followup`, `AuditLog`).

2. **Parent Call Consent & Fail-Closed Safety:**
   - Created additive Alembic migration `0b4c8e1f2a33_add_call_consent_and_opt_out.py` adding `call_consent` and `call_opt_out` to `parents` and `contact_authorized` to `campaign_targets`.
   - Enforced backend validation: live calling fails closed unless the student-parent relationship is primary, authorized, and not opted out.

3. **Removed Fake Chatbot Experience From Primary Calling Flow:**
   - Retired the browser Web Speech simulator from being the primary workflow.
   - Built a comprehensive, production-grade **Call Operations / AI Voice Agent Screen** (`CallOperationsPage.jsx`):
     - Voice service real-time health indicator.
     - Active absence campaign selector with live metrics.
     - Target queue and sequential dispatch controller (concurrency: 1).
     - Individual target status, direct call dispatch, and demo simulation buttons.
     - Call attempt history table with instant status pills.
     - Conversation transcript modal showing speaker turns, confidence, Groq classification, and follow-up flags.
     - Clear `[DEMO]` labeling for simulated records to prevent academic fabrication.

4. **Added Dedicated Admin Screens:**
   - **Parent & Guardian Directory (`ParentsPage.jsx`):** View all verified guardian contacts, review and toggle consent/opt-out status.
   - **Parent Follow-up & Callback Management (`FollowupsPage.jsx`):** Track callback requests, disputed attendance, and take action (Mark Done / Cancel / Dial Screen).
   - Connected all screens to `App.jsx` with full RBAC clearance checks.

5. **Fixed Configuration & Startup Scripts:**
   - Resolved port mismatch: unified both `voice-agent/run_server.ps1` and `voice-agent/run_tunnel.ps1` to port `8001`.
   - Updated `run_tunnel.ps1` with dynamic `ngrok` path resolution from system PATH or WinGet packages.
   - Added `scripts/start_voice.ps1` and updated `scripts/start_dev.ps1` to launch all three services (Backend, Voice Agent, Frontend) in coordinated terminal windows.
   - Verified that `scripts/check.ps1` runs the entire test suite and compiler checks without errors.

---

## 2. Which Features Genuinely Work

| Module / Feature | Execution Status | Real Implementation Details |
| :--- | :--- | :--- |
| **User Authentication & RBAC** | Genuinely Functional | JWT-based auth, Argon2/Bcrypt password hashing, Role hierarchy (SUPER_ADMIN, ADMIN, TEACHER), permission scopes. |
| **Class & Student Management** | Genuinely Functional | Full CRUD, class scoping, student listing, search, and details. |
| **Parent & Guardian Management** | Genuinely Functional | Verified phone numbers, relationship mapping, explicit call consent granting and revoking. |
| **Attendance Import & Parsing** | Genuinely Functional | Multi-format parser (CSV, XLSX, XLS, PDF tables, DOCX tables) with student matching, duplicate detection, and summary generation. |
| **Live Roll Call Terminal** | Genuinely Functional | Faculty roll call screen with present/absent quick toggles, percentage calculations, and direct call trigger. |
| **Campaign & Queue Management** | Genuinely Functional | Creates absence campaigns, computes attendance thresholds (e.g. <75%), creates targets, validates contact authorization, and supports Start / Pause / Stop / Sequential dispatch. |
| **Call Operations & Transcripts** | Genuinely Functional | Real-time attempt listing, provider Call SID tracking, turn-by-turn conversation viewer, AI sentiment, and category badges. |
| **Follow-up & Callback Management**| Genuinely Functional | Automatically schedules follow-up tasks from AI call analysis, priority tagging, and completion status transitions. |
| **Voice Agent Hindi/Hinglish Core**| Genuinely Functional | Deepgram Nova-3 multilingual streaming STT, Groq API reasoning (`openai/gpt-oss-20b`), Edge Neural TTS (`hi-IN-MadhurNeural`), and Twilio audio streaming handler. |
| **Automated Test Suites** | Genuinely Functional | 29 passing backend tests, 20 passing voice agent tests, 0 ESLint errors, clean production Vite build. |

---

## 3. Which Features Use Demo / Mock Mode

| Feature | Demonstration Mode Details |
| :--- | :--- |
| **Default Telephony Provider** | Uses `MockCallingProvider` when `REAL_CALLS_ENABLED=false` (safe default). Generates deterministic provider IDs (`demo-{attempt_id}`) and transitions to `RINGING` without incurring Twilio charges or calling real numbers. |
| **Demo Call Simulation** | Executed via `/api/v1/calls/simulate-demo` or `/api/v1/calls/dispatch-target/{id}` when real calling is disabled. Generates authentic Hindi/Hinglish conversation turns matching BBS College persona, runs AI response classification (`MEDICAL_REASON`, `CALLBACK_REQUESTED`, `WILL_ATTEND`, etc.), and persists real database records clearly marked as `is_demo=True`. |
| **Faculty Voice Commands Tool** | Secondary tool inside Call Operations using browser Web Speech API for dictating commands (e.g. *"Roll 101 absent"*). Works in supported Chromium browsers; falls back to text input when speech recognition is unavailable. |

---

## 4. Required External Credentials (For Real Live Telephony)

When running locally in **Demo/Mock mode**, **NO external credentials are required**.

To execute **real, live telephone calls** to an actual phone number, provide these credentials in `voice-agent/.env`:

1. **Twilio Telephony (Live Call Dispatch & Audio Streaming):**
   - `TWILIO_ACCOUNT_SID`: Account SID from Twilio Console.
   - `TWILIO_AUTH_TOKEN`: Auth Token from Twilio Console.
   - `TWILIO_FROM_NUMBER`: E.164 Twilio phone number with voice capabilities.
2. **Deepgram (Streaming Speech-to-Text):**
   - `DEEPGRAM_API_KEY`: API key from Deepgram Console (Nova-3 multilingual model).
3. **Groq Cloud (Dialogue Reasoning & Post-Call Response Analysis):**
   - `GROQ_API_KEY`: API key from Groq Console (`openai/gpt-oss-20b` or `llama-3.3-70b-versatile`).
4. **Public Tunnel Domain (For Twilio Webhook Delivery):**
   - `PUBLIC_BASE_URL`: e.g. `https://your-domain.ngrok-free.dev`
5. **Safety Switches (Must be explicitly turned on):**
   - `REAL_CALLS_ENABLED=true`
   - `EXTERNAL_AI_PROCESSING_APPROVED=true`

---

## 5. Exact Commands to Start All Services

### Step 0: Run System Integrity Checks
Open PowerShell in the project root:
```powershell
powershell -File scripts\check.ps1
```
*Expected output: All 29 backend tests pass, all 20 voice-agent tests pass, frontend lints and builds with 0 errors.*

---

### Option A: One-Click Launch (Recommended for Demo)
Open a single PowerShell terminal as Administrator or standard user in the project root:
```powershell
powershell -File scripts\start_dev.ps1
```
This automatically opens three coordinated terminal windows:
1. **Backend API:** `http://127.0.0.1:8000` (Swagger docs at `http://127.0.0.1:8000/docs`)
2. **AI Voice Agent:** `http://127.0.0.1:8001` (Health at `http://127.0.0.1:8001/health`)
3. **Vite Frontend:** `http://localhost:5173`

---

### Option B: Manual Multi-Window Launch

#### Terminal 1 — PostgreSQL Database (if not running as a Windows Service)
Ensure PostgreSQL is active on port `5432`:
```powershell
# If using Windows Service:
net start postgresql-x64-16
# Or verify connection:
Test-NetConnection -ComputerName localhost -Port 5432
```

#### Terminal 2 — FastAPI Backend
```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
# Apply migrations:
alembic upgrade head
# Start server:
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Terminal 3 — AI Telephony Voice Agent
```powershell
Set-Location voice-agent
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.telephony.server:app --host 127.0.0.1 --port 8001
```

#### Terminal 4 — Frontend Client
```powershell
Set-Location frontend
npm run dev
```

---

## 6. Demonstration Walkthrough (For Professor & External Examiner)

### Flow 1: Sign In & Command HUD
1. Navigate to `http://localhost:5173`.
2. Sign in with your administrator credentials.
3. Review the **Command HUD / Dashboard**: notice real metrics for classes, enrolled students, attendance rate, active campaigns, and follow-ups.

### Flow 2: Live Roll Call & Absence Marking
1. Click **Roll Call Terminal** in the top navigation.
2. Select a class (e.g. `CSE-3A`) and the current date.
3. Mark a student absent (e.g. *Rahul Sharma*).
4. Notice the instant percentage update and notice the **Call Guardian** action button appear for absent students.

### Flow 3: Campaign Review & Target Verification
1. Click **Campaigns** in the navigation.
2. Create or open an absence campaign for today's date.
3. View the generated targets: verify that only absent students with verified, authorized guardian phone numbers appear as eligible.

### Flow 4: Call Operations & AI Voice Conversation
1. Click **Call Operations** in the navigation (or the top **AI Calling** island button).
2. Note the **Voice Telephony Status**: shows connectivity to `127.0.0.1:8001`, Groq LLM model (`openai/gpt-oss-20b`), Edge Neural TTS (`hi-IN-MadhurNeural`), and Deepgram Nova-3.
3. Select your active campaign.
4. Click **Call Guardian** on the eligible student target:
   - In demo mode, it runs the multi-turn Hindi/Hinglish dialog with BBS College persona:
     - *Agent:* "Namaste ji! Main BBS College of Engineering and Technology ke attendance department se bol raha hoon. Kya meri baat Rahul ke guardian se ho rahi hai?"
     - *Parent:* "Haan ji namaste, main Rahul ka father bol raha hoon..."
     - *Agent:* "Ji, aapko inform karna tha ki Rahul ki aaj college attendance mark nahi hui hai. Kya aap absence ka reason batana chahenge?"
     - *Parent:* "Uski tabiyat kharab thi, bukhar tha."
     - *Agent:* "Ji samajh gaya. Humne medical leave note kar li hai..."
5. Inspect the **Conversation Transcript**: verify turn-by-turn speech, confidence scores, Groq AI response classification (`MEDICAL_REASON`), and sentiment.

### Flow 5: Parent Consent & Follow-ups
1. Click **Parents & Consent**: demonstrate how administrators can grant or revoke call consent, showing that calling fails closed if authorization is revoked.
2. Click **Follow-ups**: demonstrate how callback requests or disputed attendance cases are automatically queued for administrative action.

---

## 7. How to Test a Single Authorized Live Call (Optional with Credentials)

When live telephony testing is desired:
1. Ensure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` are configured in `voice-agent/.env`.
2. Ensure `DEEPGRAM_API_KEY` and `GROQ_API_KEY` are configured.
3. In a separate terminal, launch the public tunnel:
   ```powershell
   Set-Location voice-agent
   powershell -File run_tunnel.ps1 -Port 8001
   ```
4. Copy the public HTTPS URL (e.g. `https://xxxx.ngrok-free.dev`) and set `PUBLIC_BASE_URL` in `voice-agent/.env`.
5. Set `REAL_CALLS_ENABLED=true` and `EXTERNAL_AI_PROCESSING_APPROVED=true` in `backend/.env` and `voice-agent/.env`.
6. Restart backend and voice-agent servers.
7. Open **Parents & Consent**, update the target guardian phone number to your own verified personal mobile phone (in E.164 format: `+91XXXXXXXXXX`), and ensure consent is **Granted**.
8. Go to **Call Operations**, click **Call Guardian**. Your phone will ring, and the AI agent will converse in Hindi/Hinglish.

---

## 8. Test Execution Results

```text
Backend Pytest Suite:
============================= 29 passed in 1.82s =============================
- tests/test_attendance_excel_parser.py: 5 passed
- tests/test_attendance_file_parser.py: 3 passed
- tests/test_calling_workflow.py: 6 passed (Mock provider, fail-closed safety, E.164 check, factory, webhook completion, Hindi dialog simulation)
- tests/test_error_handlers.py: 1 passed
- tests/test_health.py: 2 passed
- tests/test_leave.py: 2 passed
- tests/test_rule_engine.py: 3 passed
- tests/test_security_settings.py: 5 passed
- tests/test_student_import_service.py: 2 passed

Voice Agent Pytest Suite:
======================== 20 passed, 1 warning in 1.64s ========================
- tests/test_backend_client.py: 1 passed
- tests/test_call_context.py: 3 passed
- tests/test_main.py: 1 passed
- tests/test_telephony.py: 15 passed

Frontend Checks:
- ESLint: 0 errors, 0 warnings (Clean exit)
- Vite Build: 1899 modules transformed, built in 616ms (Clean exit)
```

---

## 9. Current Scope & Known Limitations

1. **Sequential Outbound Calling:** The system uses controlled sequential dispatch (default concurrency: 1) to respect Twilio carrier throughput limits and ensure safe demonstration in college environments.
2. **Multi-Tenant Scoping:** Academic scopes (college, department, class) are strictly enforced at the backend database query level; instructors cannot access student records outside their assigned department.
3. **Audio File Persistence:** Full raw telephone audio recordings (.mp3/.wav) are not retained permanently on disk by default to comply with student privacy policies; complete text transcripts and AI turn analyses are preserved in PostgreSQL.

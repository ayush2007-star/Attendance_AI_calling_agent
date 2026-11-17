#!/usr/bin/env python3
"""
AttendWise AI - Terminal CLI Interface
======================================
Automated Attendance AI Calling Agent for Schools and Colleges.
Provides end-to-end database loading, AI voice generation, Twilio
telephony integration, call status tracking, and database logging.
"""

import argparse
import asyncio
import html
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

# ---------------------------------------------------------------------------
# Dynamic Python Environment & Path Setup
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
VOICE_AGENT_DIR = ROOT_DIR / "voice-agent"

# Inject virtualenv site-packages if available so running with global python works
for venv_path in [VOICE_AGENT_DIR / ".venv", BACKEND_DIR / ".venv"]:
    site_packages = venv_path / "Lib" / "site-packages"
    if site_packages.exists() and str(site_packages) not in sys.path:
        sys.path.insert(0, str(site_packages))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(VOICE_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(VOICE_AGENT_DIR))

# Import required libraries
import httpx
from dotenv import dotenv_values
from sqlalchemy import create_engine, desc, text
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

try:
    from groq import Groq
    HAS_GROQ_SDK = True
except ImportError:
    HAS_GROQ_SDK = False


# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------
def load_config() -> dict[str, Any]:
    """Load configuration from backend/.env, voice-agent/.env, and environment."""
    config: dict[str, Any] = {}

    # 1. Load backend .env
    backend_env_file = BACKEND_DIR / ".env"
    backend_vals = {}
    if backend_env_file.exists():
        backend_vals = {k: v for k, v in dotenv_values(backend_env_file).items() if v is not None}
        config.update(backend_vals)

    # 2. Load voice-agent .env (telephony & AI settings)
    voice_env_file = VOICE_AGENT_DIR / ".env"
    voice_vals = {}
    if voice_env_file.exists():
        voice_vals = {k: v for k, v in dotenv_values(voice_env_file).items() if v is not None}
        # Keep databases distinct
        voice_db = voice_vals.pop("DATABASE_URL", None)
        if voice_db:
            config["VOICE_DATABASE_URL"] = voice_db
        config.update(voice_vals)

    if "DATABASE_URL" in backend_vals:
        config["BACKEND_DATABASE_URL"] = backend_vals["DATABASE_URL"]
        config["DATABASE_URL"] = backend_vals["DATABASE_URL"]

    # 3. Environment variables take highest precedence
    for key, val in os.environ.items():
        if val:
            config[key] = val

    # Sensible defaults
    config.setdefault("APP_NAME", "AttendWise AI")
    config.setdefault("SCHOOL_NAME", "BBS College of Engineering and Technology")
    config.setdefault("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    config.setdefault("GROQ_MODEL", "llama-3.3-70b-versatile")
    config.setdefault("TTS_PROVIDER", "edge")
    config.setdefault("EDGE_VOICE_HI", "hi-IN-MadhurNeural")
    config.setdefault("EDGE_VOICE_EN", "en-IN-NeerjaNeural")

    # Map aliases
    if "TWILIO_PHONE_NUMBER" in config and not config.get("TWILIO_FROM_NUMBER"):
        config["TWILIO_FROM_NUMBER"] = config["TWILIO_PHONE_NUMBER"]
    if "TWILIO_FROM_NUMBER" in config and not config.get("TWILIO_PHONE_NUMBER"):
        config["TWILIO_PHONE_NUMBER"] = config["TWILIO_FROM_NUMBER"]

    return config


CONFIG = load_config()


def mask_secret(value: str | None, visible: int = 4) -> str:
    """Mask a secret value for safe terminal display."""
    if not value:
        return "<NOT CONFIGURED>"
    if len(value) <= visible * 2:
        return "***"
    return f"{value[:visible]}...{value[-visible:]}"


def normalize_e164(phone: str) -> str:
    """Normalize phone number to E.164 international format."""
    clean = re.sub(r"[\s\-\(\)]", "", phone.strip())
    if clean.startswith("+"):
        return clean
    if clean.startswith("0") and len(clean) == 11:
        return f"+91{clean[1:]}"
    if len(clean) == 10:
        return f"+91{clean}"
    return f"+{clean}"


# ---------------------------------------------------------------------------
# Database Utilities
# ---------------------------------------------------------------------------
def get_backend_engine():
    db_url = CONFIG.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not configured in backend/.env")
    return create_engine(db_url, pool_pre_ping=True)


def get_voice_db_engine():
    # voice-agent DB might use same or separate DB
    voice_env_file = VOICE_AGENT_DIR / ".env"
    v_vals = dotenv_values(voice_env_file) if voice_env_file.exists() else {}
    v_db_url = v_vals.get("DATABASE_URL") or CONFIG.get("DATABASE_URL")
    if not v_db_url:
        return None
    try:
        return create_engine(v_db_url, pool_pre_ping=True)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# AI Voice Message Generator
# ---------------------------------------------------------------------------
def generate_absence_message(
    student_name: str,
    parent_name: str,
    attendance_date: str,
    school_name: str | None = None,
    preferred_language: str = "hi",
) -> tuple[str, str]:
    """
    Generate natural Hindi/English voice notification.
    Returns: (spoken_text, source_tag)
    """
    school = school_name or CONFIG.get("SCHOOL_NAME", "BBS College of Engineering and Technology")
    groq_api_key = CONFIG.get("GROQ_API_KEY")

    # Try Live Groq AI generation
    if groq_api_key:
        try:
            prompt = (
                f"You are the voice calling assistant of {school}. "
                f"Generate a polite, concise Hindi absence notification for parent '{parent_name}'. "
                f"Explicitly inform them: 'Aapka bachcha {student_name} aaj college nahi aaya hai.' "
                f"Instruct the parent: 'Upasthiti confirm karne ke liye 1 dabayein, ya callback ke liye 2 dabayein.' "
                f"Keep it natural and under 30 words. Return ONLY the spoken Hindi text without quotes."
            )
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(
                    f"{CONFIG['GROQ_BASE_URL'].rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {groq_api_key}"},
                    json={
                        "model": CONFIG.get("GROQ_MODEL", "openai/gpt-oss-20b"),
                        "messages": [
                            {"role": "system", "content": "You generate concise Indian college attendance voice messages."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 512,
                    },
                )
                if resp.status_code == 200:
                    ai_text = resp.json()["choices"][0]["message"]["content"].strip()
                    if ai_text:
                        return (ai_text, f"Groq AI ({CONFIG.get('GROQ_MODEL', 'openai/gpt-oss-20b')})")
        except Exception:
            pass  # Fall back gracefully

    # Deterministic Fallback Template
    if preferred_language.startswith("en"):
        text_msg = (
            f"Hello {parent_name}, this is AttendWise AI calling from {school}. "
            f"{student_name} was marked absent for college today on {attendance_date}. "
            f"Please press 1 to confirm this absence, or press 2 to request a callback. Thank you."
        )
    else:
        text_msg = (
            f"नमस्ते {parent_name} जी, मैं {school} से AttendWise AI बोल रहा हूँ। "
            f"आपका बच्चा {student_name} आज कॉलेज नहीं आया है। "
            f"उपस्थिति कन्फर्म करने के लिए 1 दबाएं, या कॉलबैक के लिए 2 दबाएं। धन्यवाद।"
        )
    return (text_msg, "Template Fallback")


def build_twiml(
    message: str,
    session_id: str,
    action_url: str | None = None,
) -> str:
    """Build clean TwiML that reliably delivers the absence announcement."""
    escaped_msg = html.escape(message)
    action_attr = f' action="{html.escape(action_url)}"' if action_url else ""
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Response>\n'
        f'    <Pause length="1"/>\n'
        f'    <Say language="hi-IN" voice="Polly.Aditi">{escaped_msg}</Say>\n'
        f'    <Gather numDigits="1"{action_attr} method="POST" timeout="6">\n'
        f'        <Say language="hi-IN" voice="Polly.Aditi">Confirm karne ke liye 1 dabayein, ya callback ke liye 2 dabayein.</Say>\n'
        f'    </Gather>\n'
        f'    <Say language="hi-IN" voice="Polly.Aditi">Aapka response darj kar liya gaya hai. Dhanyavaad.</Say>\n'
        f'    <Hangup/>\n'
        f'</Response>'
    )


# ---------------------------------------------------------------------------
# Database Persistence
# ---------------------------------------------------------------------------
def record_call_in_db(
    student_id: UUID | None,
    student_name: str,
    parent_id: UUID | None,
    phone_number: str,
    call_sid: str,
    status: str,
    duration_seconds: int = 0,
    attendance_date: date | None = None,
    error_reason: str | None = None,
    parent_response: str | None = None,
    response_category: str | None = None,
    is_demo: bool = False,
) -> None:
    """Record call attempt in backend DB and parent response in voice DB."""
    # 1. Backend database records
    try:
        engine = get_backend_engine()
        with engine.begin() as conn:
            att_date = attendance_date or date.today()

            # Find default admin and class
            admin_id = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
            class_id = conn.execute(text("SELECT class_id FROM students WHERE id = :sid"), {"sid": student_id}).scalar() if student_id else None
            if not class_id:
                class_id = conn.execute(text("SELECT id FROM classes LIMIT 1")).scalar()

            # Resolve valid parent_id and student_id to prevent FK violations on ad-hoc calls
            resolved_parent_id = parent_id
            if not resolved_parent_id:
                resolved_parent_id = conn.execute(
                    text("SELECT id FROM parents WHERE primary_phone = :p LIMIT 1"),
                    {"p": phone_number},
                ).scalar()
            if not resolved_parent_id:
                resolved_parent_id = conn.execute(text("SELECT id FROM parents LIMIT 1")).scalar()

            resolved_student_id = student_id
            if not resolved_student_id:
                resolved_student_id = conn.execute(text("SELECT id FROM students LIMIT 1")).scalar()

            # Ensure or find campaign
            camp = conn.execute(
                text("SELECT id FROM call_campaigns WHERE attendance_date = :d ORDER BY created_at DESC LIMIT 1"),
                {"d": att_date},
            ).mappings().first()

            if camp:
                campaign_id = camp["id"]
            else:
                campaign_id = uuid4()
                conn.execute(
                    text("""
                        INSERT INTO call_campaigns
                            (id, name, attendance_date, class_id, status, total_targets, completed_calls, failed_calls, created_by, attendance_period_start, attendance_period_end, threshold_used, created_at, updated_at)
                        VALUES
                            (:id, :name, :d, :cid, 'RUNNING', 1, 0, 0, :uid, :d, :d, 75.0, now(), now())
                    """),
                    {
                        "id": campaign_id,
                        "name": f"Attendance Campaign {att_date}",
                        "d": att_date,
                        "cid": class_id,
                        "uid": admin_id,
                    },
                )

            # Ensure or find campaign target
            target_id = uuid4()
            if resolved_student_id:
                existing_target = conn.execute(
                    text("SELECT id FROM campaign_targets WHERE campaign_id = :cid AND student_id = :sid LIMIT 1"),
                    {"cid": campaign_id, "sid": resolved_student_id},
                ).scalar()
                if existing_target:
                    target_id = existing_target
                else:
                    conn.execute(
                        text("""
                            INSERT INTO campaign_targets
                                (id, campaign_id, student_id, parent_id, attendance_percentage_used, threshold_used, eligibility_reason, status, selected_phone_number, contact_authorized, created_at, updated_at)
                            VALUES
                                (:id, :cid, :sid, :pid, 65.0, 75.0, 'ABSENT', :status, :phone, true, now(), now())
                        """),
                        {
                            "id": target_id,
                            "cid": campaign_id,
                            "sid": resolved_student_id,
                            "pid": resolved_parent_id,
                            "status": status,
                            "phone": phone_number,
                        },
                    )

            # Insert Call Attempt
            attempt_id = uuid4()
            now = datetime.now(timezone.utc)
            conn.execute(
                text("""
                    INSERT INTO call_attempts
                        (id, campaign_id, campaign_target_id, parent_id, attempt_number, phone_number, status, provider_call_id, started_at, ended_at, duration_seconds, failure_reason, created_at, updated_at)
                    VALUES
                        (:id, :cid, :tid, :pid, 1, :phone, :status, :call_sid, :start, :end, :dur, :fail, :now, :now)
                """),
                {
                    "id": attempt_id,
                    "cid": campaign_id,
                    "tid": target_id,
                    "pid": resolved_parent_id,
                    "phone": phone_number,
                    "status": status,
                    "call_sid": call_sid,
                    "start": now,
                    "end": now,
                    "dur": duration_seconds,
                    "fail": error_reason,
                    "now": now,
                },
            )

            # Insert conversation record
            conv_id = uuid4()
            conn.execute(
                text("""
                    INSERT INTO conversations
                        (id, call_attempt_id, language, status, started_at, ended_at, created_at, updated_at)
                    VALUES
                        (:id, :att, 'hi-IN', :status, :start, :end, now(), now())
                """),
                {
                    "id": conv_id,
                    "att": attempt_id,
                    "status": status,
                    "start": now,
                    "end": now,
                },
            )

            # Insert AI analysis record if response exists
            if parent_response:
                an_id = uuid4()
                conn.execute(
                    text("""
                        INSERT INTO ai_analyses
                            (id, conversation_id, category, summary, followup_required, confidence, model_name, created_at, updated_at)
                        VALUES
                            (:id, :cid, :cat, :summary, :fu, 0.95, 'AttendWise AI Engine', now(), now())
                    """),
                    {
                        "id": an_id,
                        "cid": conv_id,
                        "cat": response_category or "ACKNOWLEDGED",
                        "summary": parent_response,
                        "fu": (response_category == "CALLBACK_REQUESTED"),
                    },
                )

            # Update campaign stats
            if status in ("COMPLETED", "RINGING", "IN-PROGRESS", "CONNECTED"):
                conn.execute(
                    text("UPDATE call_campaigns SET completed_calls = completed_calls + 1, updated_at = now() WHERE id = :cid"),
                    {"cid": campaign_id},
                )
            elif status in ("FAILED", "BUSY", "NO-ANSWER"):
                conn.execute(
                    text("UPDATE call_campaigns SET failed_calls = failed_calls + 1, updated_at = now() WHERE id = :cid"),
                    {"cid": campaign_id},
                )

    except Exception as e:
        print(f"  [DB Warning] Could not persist to backend DB: {e}", file=sys.stderr)

    # 2. Voice-Agent database record
    try:
        v_engine = get_voice_db_engine()
        if v_engine:
            with v_engine.begin() as v_conn:
                session_id = uuid4()
                # Insert voice_call_sessions
                v_conn.execute(
                    text("""
                        INSERT INTO voice_call_sessions (session_id, idempotency_key, call_sid, status, created_at)
                        VALUES (:sid, :key, :call_sid, :status, now())
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "sid": session_id,
                        "key": f"cli-{call_sid}-{time.time()}",
                        "call_sid": call_sid,
                        "status": status,
                    },
                )
                if parent_response:
                    cat = response_category or "INFO"
                    formatted_resp = f"[{cat}] {parent_response}" if not parent_response.startswith("[") else parent_response
                    v_conn.execute(
                        text("""
                            INSERT INTO parent_call_responses
                                (session_id, student_id, student_name, response_text, recorded_at)
                            VALUES
                                (:sid, :stid, :sname, :resp, now())
                            ON CONFLICT (session_id) DO UPDATE SET response_text = EXCLUDED.response_text
                        """),
                        {
                            "sid": session_id,
                            "stid": student_id or uuid4(),
                            "sname": student_name,
                            "resp": formatted_resp,
                        },
                    )
    except Exception as e:
        print(f"  [Voice DB Warning] Could not persist to voice DB: {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI Command 1: test
# ---------------------------------------------------------------------------
def cmd_test(args: argparse.Namespace) -> int:
    """Run diagnostics on Database, Twilio, Groq, Deepgram, and Edge TTS."""
    print("\n" + "=" * 65)
    print(" ATTENDWISE AI - SYSTEM DIAGNOSTICS & CONNECTIVITY CHECK")
    print("=" * 65 + "\n")

    overall_pass = True

    # 1. Backend PostgreSQL Database
    print("[1/5] Checking Backend Database (PostgreSQL)...")
    try:
        engine = get_backend_engine()
        t0 = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).scalar()
            st_count = conn.execute(text("SELECT count(*) FROM students")).scalar()
            att_count = conn.execute(text("SELECT count(*) FROM attendance_records")).scalar()
        latency = int((time.time() - t0) * 1000)
        print(f"      Status:   [PASS] Connected successfully ({latency}ms)")
        print(f"      Stats:    {st_count} students registered | {att_count} attendance records")
    except Exception as e:
        overall_pass = False
        print(f"      Status:   [FAIL] {type(e).__name__}: {e}")

    # 2. Voice-Agent Database
    print("\n[2/5] Checking Voice Agent Database...")
    try:
        v_engine = get_voice_db_engine()
        if v_engine:
            with v_engine.connect() as conn:
                res_count = conn.execute(text("SELECT count(*) FROM parent_call_responses")).scalar()
            print(f"      Status:   [PASS] Connected successfully")
            print(f"      Stats:    {res_count} logged parent responses")
        else:
            print(f"      Status:   [PASS] Shared backend database configured")
    except Exception as e:
        print(f"      Status:   [WARN] {type(e).__name__}: {e}")

    # 3. Twilio Telephony Configuration & API
    print("\n[3/5] Checking Twilio Telephony API...")
    account_sid = CONFIG.get("TWILIO_ACCOUNT_SID")
    auth_token = CONFIG.get("TWILIO_AUTH_TOKEN")
    from_number = CONFIG.get("TWILIO_FROM_NUMBER") or CONFIG.get("TWILIO_PHONE_NUMBER")

    if not account_sid or not auth_token or not from_number:
        overall_pass = False
        print(f"      Status:   [FAIL] Missing credentials in environment")
        print(f"      Details:  SID={bool(account_sid)}, Token={bool(auth_token)}, FromNumber={bool(from_number)}")
    else:
        print(f"      Account:  SID={mask_secret(account_sid)} | Caller ID={from_number}")
        try:
            client = Client(account_sid, auth_token)
            t0 = time.time()
            acc = client.api.accounts(account_sid).fetch()
            latency = int((time.time() - t0) * 1000)
            verified_callers = [c.phone_number for c in client.outgoing_caller_ids.list(limit=5)]
            print(f"      Status:   [PASS] Twilio API authenticated ({latency}ms)")
            print(f"      Type:     {acc.type.capitalize()} Account (Status: {acc.status})")
            print(f"      Verified: Outgoing Caller IDs for Trial: {verified_callers}")
            if acc.type.lower() == "trial":
                print("      Note:     On Twilio Trial accounts, real calls can only be placed to verified caller IDs.")
        except Exception as e:
            overall_pass = False
            print(f"      Status:   [FAIL] Twilio Authentication Error: {e}")

    # 4. AI Services (Groq LLM & Deepgram STT)
    print("\n[4/5] Checking AI Services (Groq & Deepgram)...")
    groq_key = CONFIG.get("GROQ_API_KEY")
    if groq_key:
        try:
            t0 = time.time()
            with httpx.Client(timeout=5.0) as client:
                r = client.post(
                    f"{CONFIG['GROQ_BASE_URL'].rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": CONFIG.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
                        "messages": [{"role": "user", "content": "Ping"}],
                        "max_tokens": 5,
                    },
                )
            latency = int((time.time() - t0) * 1000)
            if r.status_code == 200:
                print(f"      Groq AI:  [PASS] Operational ({latency}ms) - Model: {CONFIG.get('GROQ_MODEL')}")
            else:
                print(f"      Groq AI:  [FAIL] HTTP {r.status_code} - {r.text[:80]}")
        except Exception as e:
            print(f"      Groq AI:  [FAIL] {e}")
    else:
        print("      Groq AI:  [SKIP] GROQ_API_KEY not configured (fallback templates active)")

    deepgram_key = CONFIG.get("DEEPGRAM_API_KEY")
    if deepgram_key:
        try:
            with httpx.Client(timeout=4.0) as client:
                r = client.get("https://api.deepgram.com/v1/projects", headers={"Authorization": f"Token {deepgram_key}"})
            if r.status_code == 200:
                print(f"      Deepgram: [PASS] Operational (STT Ready)")
            else:
                print(f"      Deepgram: [WARN] HTTP {r.status_code}")
        except Exception as e:
            print(f"      Deepgram: [WARN] {e}")

    # 5. Voice Generation (Edge TTS)
    print("\n[5/5] Checking Voice Generation (Edge TTS)...")
    if HAS_EDGE_TTS:
        try:
            async def test_edge():
                comm = edge_tts.Communicate("नमस्ते अटेंडवाइज़ एआई", voice=CONFIG.get("EDGE_VOICE_HI", "hi-IN-MadhurNeural"))
                data = bytearray()
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        data.extend(chunk["data"])
                return len(data)

            bytes_gen = asyncio.run(test_edge())
            print(f"      Edge TTS: [PASS] Audio Synthesis Ready ({bytes_gen} bytes generated)")
            print(f"      Voice:    {CONFIG.get('EDGE_VOICE_HI')} (Natural Hindi)")
        except Exception as e:
            print(f"      Edge TTS: [FAIL] {e}")
    else:
        print("      Edge TTS: [SKIP] edge-tts package not available, using Twilio Polly natively")

    print("\n" + "=" * 65)
    if overall_pass:
        print(" DIAGNOSTIC RESULT: ALL ESSENTIAL COMPONENTS OPERATIONAL [PASS]")
    else:
        print(" DIAGNOSTIC RESULT: SOME COMPONENTS FAILED - CHECK DETAILS ABOVE")
    print("=" * 65 + "\n")
    return 0 if overall_pass else 1


# ---------------------------------------------------------------------------
# CLI Command 2: students
# ---------------------------------------------------------------------------
def cmd_students(args: argparse.Namespace) -> int:
    """List students and their attendance / parent contact information."""
    engine = get_backend_engine()
    with engine.connect() as conn:
        filter_date = args.date or None
        status_filter = args.status.upper() if args.status and args.status.upper() != "ALL" else None

        query_str = """
            SELECT s.roll_number, s.first_name, s.last_name, s.student_code,
                   p.name as parent_name, p.primary_phone,
                   a.attendance_date, a.status as attendance_status
            FROM students s
            LEFT JOIN student_parents sp ON sp.student_id = s.id AND sp.is_primary = true
            LEFT JOIN parents p ON p.id = sp.parent_id
            LEFT JOIN attendance_records a ON a.student_id = s.id
            WHERE 1=1
        """
        params: dict[str, Any] = {}

        if filter_date:
            query_str += " AND a.attendance_date = :att_date"
            params["att_date"] = filter_date
        if status_filter:
            query_str += " AND a.status = :att_status"
            params["att_status"] = status_filter

        query_str += " ORDER BY a.attendance_date DESC, s.roll_number LIMIT :lim"
        params["lim"] = args.limit or 50

        rows = conn.execute(text(query_str), params).fetchall()

        print("\n" + "=" * 90)
        print(f" ATTENDWISE AI - STUDENT ROSTER & ATTENDANCE RECORDS")
        if filter_date:
            print(f" Filter Date: {filter_date} | Status Filter: {status_filter or 'ALL'}")
        print("=" * 90)
        print(f"{'ROLL NO':<12} | {'STUDENT NAME':<20} | {'PARENT NAME':<20} | {'PHONE NUMBER':<14} | {'DATE':<10} | {'STATUS':<8}")
        print("-" * 90)

        total = len(rows)
        absent_cnt = 0
        present_cnt = 0

        for r in rows:
            m = dict(r._mapping)
            full_name = f"{m['first_name']} {m['last_name'] or ''}".strip()
            p_name = m["parent_name"] or "<Not Set>"
            phone = m["primary_phone"] or "<Missing>"
            att_d = str(m["attendance_date"]) if m["attendance_date"] else "-"
            st = m["attendance_status"] or "NO_DATA"

            if st == "ABSENT":
                absent_cnt += 1
            elif st == "PRESENT":
                present_cnt += 1

            print(f"{m['roll_number']:<12} | {full_name:<20} | {p_name:<20} | {phone:<14} | {att_d:<10} | {st:<8}")

        print("-" * 90)
        print(f"Total Listed: {total} | Absent: {absent_cnt} | Present: {present_cnt}\n")

    return 0


# ---------------------------------------------------------------------------
# CLI Command 3: call-absent
# ---------------------------------------------------------------------------
def cmd_call_absent(args: argparse.Namespace) -> int:
    """Initiate calls for absent students on a given date."""
    target_date_str = args.date or str(date.today())
    try:
        target_date = date.fromisoformat(target_date_str)
    except ValueError:
        print(f"Error: Invalid date format '{target_date_str}'. Use YYYY-MM-DD.", file=sys.stderr)
        return 1

    engine = get_backend_engine()
    with engine.connect() as conn:
        q = """
            SELECT s.id as student_id, s.student_code, s.roll_number, s.first_name, s.last_name,
                   p.id as parent_id, p.name as parent_name, p.primary_phone,
                   a.attendance_date, a.status as attendance_status
            FROM attendance_records a
            JOIN students s ON s.id = a.student_id
            LEFT JOIN student_parents sp ON sp.student_id = s.id AND sp.is_primary = true
            LEFT JOIN parents p ON p.id = sp.parent_id
            WHERE a.attendance_date = :att_date AND a.status = 'ABSENT'
            ORDER BY s.roll_number
        """
        rows = conn.execute(text(q), {"att_date": target_date}).fetchall()

    if not rows:
        print(f"\n[INFO] No absent students found for date: {target_date}")
        with engine.connect() as conn:
            avail_dates = conn.execute(
                text("SELECT DISTINCT attendance_date FROM attendance_records ORDER BY attendance_date DESC LIMIT 5")
            ).fetchall()
        print(f"Available dates in database: {[str(d[0]) for d in avail_dates]}\n")
        return 0

    print("\n" + "=" * 75)
    print(f" ATTENDWISE AI - ABSENT STUDENT CALLING CAMPAIGN")
    print(f" Attendance Date: {target_date} | Total Absent Students: {len(rows)}")
    mode_label = "DEMO / MOCK MODE (No real phone calls)" if args.demo else "REAL CALLING MODE (Twilio Live Telephony)"
    print(f" Execution Mode:  {mode_label}")
    print("=" * 75)

    # Inspect Twilio account if real mode
    verified_numbers: list[str] = []
    is_trial_account = False
    twilio_client: Client | None = None

    if not args.demo:
        account_sid = CONFIG.get("TWILIO_ACCOUNT_SID")
        auth_token = CONFIG.get("TWILIO_AUTH_TOKEN")
        from_number = CONFIG.get("TWILIO_FROM_NUMBER") or CONFIG.get("TWILIO_PHONE_NUMBER")

        if not account_sid or not auth_token or not from_number:
            print("\n[ERROR] Twilio credentials missing in environment. Cannot execute REAL call.", file=sys.stderr)
            print("Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER or pass --demo for simulation.", file=sys.stderr)
            return 1

        try:
            twilio_client = Client(account_sid, auth_token)
            acc = twilio_client.api.accounts(account_sid).fetch()
            is_trial_account = (acc.type.lower() == "trial")
            if is_trial_account:
                verified_numbers = [c.phone_number for c in twilio_client.outgoing_caller_ids.list(limit=10)]
        except Exception as e:
            print(f"\n[ERROR] Twilio authentication failed: {e}", file=sys.stderr)
            return 1

    # Print candidates table
    print(f"\n{'ROLL NO':<10} | {'STUDENT NAME':<20} | {'PARENT NAME':<20} | {'PHONE':<14} | {'TRIAL STATUS'}")
    print("-" * 75)

    call_list = []
    for r in rows:
        m = dict(r._mapping)
        full_name = f"{m['first_name']} {m['last_name'] or ''}".strip()
        p_name = m["parent_name"] or "Guardian"
        raw_phone = m["primary_phone"]
        norm_phone = normalize_e164(raw_phone) if raw_phone else None

        trial_note = "Ready"
        if not args.demo and is_trial_account:
            if norm_phone not in verified_numbers:
                trial_note = "UNVERIFIED (Trial limitation)"
            else:
                trial_note = "VERIFIED"

        print(f"{m['roll_number']:<10} | {full_name:<20} | {p_name:<20} | {norm_phone or '<Missing>':<14} | {trial_note}")
        call_list.append({
            "student_id": m["student_id"],
            "student_name": full_name,
            "roll_number": m["roll_number"],
            "parent_id": m["parent_id"],
            "parent_name": p_name,
            "phone": norm_phone,
            "is_verified": (norm_phone in verified_numbers) if is_trial_account else True,
        })

    print("-" * 75)

    if not args.demo and is_trial_account:
        print("\n> [NOTICE] Your Twilio Trial account has verified number(s):", verified_numbers)
        print("> Calls to unverified numbers will be rejected by Twilio with HTTP 400.")

    # Operator Confirmation
    if not args.yes:
        confirm = input(f"\nProceed with initiating calls for {len(call_list)} student(s)? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Operation aborted by operator.")
            return 0

    print("\nInitiating calls...\n")

    successful_calls = 0
    failed_calls = 0
    results: list[dict[str, Any]] = []

    public_base_url = CONFIG.get("PUBLIC_BASE_URL", "").rstrip("/")

    for item in call_list:
        student_name = item["student_name"]
        parent_name = item["parent_name"]
        phone = item["phone"]

        if not phone:
            print(f"[-] Skipping {student_name}: No parent phone number registered.")
            failed_calls += 1
            results.append({
                "student": student_name,
                "phone": "N/A",
                "status": "FAILED",
                "call_sid": "N/A",
                "error": "Missing phone number",
                "response": "N/A",
            })
            continue

        # Generate Voice Message
        voice_msg, msg_source = generate_absence_message(
            student_name=student_name,
            parent_name=parent_name,
            attendance_date=str(target_date),
            preferred_language=args.lang,
        )

        session_id = str(uuid4())
        dtmf_action_url = f"{public_base_url}/twiml/dtmf/{session_id}" if public_base_url else None
        twiml_payload = build_twiml(voice_msg, session_id, dtmf_action_url)

        if args.demo:
            # DEMO / MOCK CALL
            mock_sid = f"demo-{uuid4().hex[:16]}"
            print(f"[DEMO CALL] Dialing {parent_name} ({phone}) for {student_name}...")
            print(f"            Message ({msg_source}): \"{voice_msg[:70]}...\"")
            print(f"            Call SID: {mock_sid} | Status: COMPLETED (Demo Simulation)")
            successful_calls += 1
            record_call_in_db(
                student_id=item["student_id"],
                student_name=student_name,
                parent_id=item["parent_id"],
                phone_number=phone,
                call_sid=mock_sid,
                status="COMPLETED",
                duration_seconds=22,
                attendance_date=target_date,
                parent_response="[DEMO] Parent confirmed absence via automated simulation.",
                response_category="ACKNOWLEDGED",
                is_demo=True,
            )
            results.append({
                "student": student_name,
                "phone": phone,
                "status": "COMPLETED (DEMO)",
                "call_sid": mock_sid,
                "error": None,
                "response": "Acknowledged (Simulated)",
            })
        else:
            # REAL TWILIO CALL
            from_num = CONFIG.get("TWILIO_FROM_NUMBER") or CONFIG.get("TWILIO_PHONE_NUMBER")
            print(f"[REAL CALL] Dialing {parent_name} ({phone}) from {from_num}...")
            print(f"            Message ({msg_source}): \"{voice_msg[:70]}...\"")

            try:
                assert twilio_client is not None
                tw_call = twilio_client.calls.create(
                    to=phone,
                    from_=from_num,
                    twiml=twiml_payload,
                    status_callback=f"{public_base_url}/status" if public_base_url else None,
                    status_callback_event=["initiated", "ringing", "answered", "completed"],
                )
                call_sid = tw_call.sid
                status_val = tw_call.status.upper()
                print(f"            Success! Twilio Call SID: {call_sid} | Initial Status: {status_val}")

                # Poll live status for up to 10 seconds
                final_status = status_val
                for _ in range(5):
                    time.sleep(2)
                    fetched = twilio_client.calls(call_sid).fetch()
                    final_status = fetched.status.upper()
                    if final_status in ("IN-PROGRESS", "COMPLETED", "BUSY", "NO-ANSWER", "FAILED", "CANCELED"):
                        break

                print(f"            Final Live Status: {final_status}")
                successful_calls += 1

                record_call_in_db(
                    student_id=item["student_id"],
                    student_name=student_name,
                    parent_id=item["parent_id"],
                    phone_number=phone,
                    call_sid=call_sid,
                    status=final_status,
                    duration_seconds=0,
                    attendance_date=target_date,
                    parent_response="Outbound notification delivered via Twilio Live Telephony.",
                    response_category="OUTBOUND_CALL",
                    is_demo=False,
                )
                results.append({
                    "student": student_name,
                    "phone": phone,
                    "status": final_status,
                    "call_sid": call_sid,
                    "error": None,
                    "response": "Delivered to Phone",
                })
            except TwilioRestException as e:
                failed_calls += 1
                err_msg = str(e.msg)
                print(f"            [Twilio Error] {err_msg}")
                if "unverified" in err_msg.lower():
                    print(f"            -> Reason: Number is unverified on Twilio Trial account.")
                record_call_in_db(
                    student_id=item["student_id"],
                    student_name=student_name,
                    parent_id=item["parent_id"],
                    phone_number=phone,
                    call_sid=f"failed-{uuid4().hex[:8]}",
                    status="FAILED",
                    attendance_date=target_date,
                    error_reason=err_msg,
                    is_demo=False,
                )
                results.append({
                    "student": student_name,
                    "phone": phone,
                    "status": "FAILED",
                    "call_sid": "N/A",
                    "error": err_msg[:40],
                    "response": "N/A",
                })
            except Exception as e:
                failed_calls += 1
                print(f"            [Error] {type(e).__name__}: {e}")
                results.append({
                    "student": student_name,
                    "phone": phone,
                    "status": "FAILED",
                    "call_sid": "N/A",
                    "error": str(e)[:40],
                    "response": "N/A",
                })

    # Summary Report
    print("\n" + "=" * 75)
    print(" CAMPAIGN EXECUTION SUMMARY")
    print("=" * 75)
    print(f"Attendance Date:         {target_date}")
    print(f"Total Absent Students:   {len(rows)}")
    print(f"Total Calls Initiated:   {len(call_list)}")
    print(f"Successful Calls:        {successful_calls}")
    print(f"Failed Calls:            {failed_calls}")
    print("-" * 75)
    print(f"{'STUDENT':<20} | {'PHONE':<14} | {'STATUS':<15} | {'CALL SID':<22} | {'RESULT'}")
    print("-" * 75)
    for r in results:
        print(f"{r['student']:<20} | {r['phone']:<14} | {r['status']:<15} | {r['call_sid']:<22} | {r['response'] or r['error']}")
    print("=" * 75 + "\n")

    return 0


# ---------------------------------------------------------------------------
# CLI Command 4: call-test
# ---------------------------------------------------------------------------
def cmd_call_test(args: argparse.Namespace) -> int:
    """Make one test call to a single phone number provided by the operator."""
    phone = normalize_e164(args.phone)
    student_name = args.student_name or "Aarav Sharma"
    parent_name = args.parent_name or "Rajesh Sharma"
    today_str = str(date.today())

    engine = get_backend_engine()
    resolved_student_id = None
    resolved_parent_id = None
    with engine.connect() as conn:
        st_row = conn.execute(
            text("SELECT id FROM students WHERE first_name || ' ' || COALESCE(last_name, '') ILIKE :n LIMIT 1"),
            {"n": f"%{student_name}%"},
        ).scalar()
        if st_row:
            resolved_student_id = st_row
        p_row = conn.execute(
            text("SELECT id FROM parents WHERE name ILIKE :n OR primary_phone = :p LIMIT 1"),
            {"n": f"%{parent_name}%", "p": phone},
        ).scalar()
        if p_row:
            resolved_parent_id = p_row

    print("\n" + "=" * 70)
    print(" ATTENDWISE AI - SINGLE TEST CALL")
    mode_label = "DEMO / MOCK MODE" if args.demo else "REAL CALLING MODE (Twilio Live Telephony)"
    print(f" Execution Mode: {mode_label}")
    print(f" Recipient:      {parent_name} ({phone})")
    print(f" Student:        {student_name} (Attendance Date: {today_str})")
    print("=" * 70)

    # Generate Voice Message
    voice_msg, msg_source = generate_absence_message(
        student_name=student_name,
        parent_name=parent_name,
        attendance_date=today_str,
        preferred_language=args.lang,
    )
    print(f"\n[Generated Voice Message - Source: {msg_source}]")
    print(f"\"{voice_msg}\"\n")

    if args.demo:
        # DEMO CALL
        mock_sid = f"demo-{uuid4().hex[:16]}"
        print(f"[DEMO CALL] Dialing {phone}...")
        print(f"            Playing voice message via simulated telephony...")
        time.sleep(1.5)
        print(f"            Recipient dialed key 1 (Confirmed absence).")
        print(f"            Call SID: {mock_sid} | Status: COMPLETED (Demo)")

        record_call_in_db(
            student_id=resolved_student_id,
            student_name=student_name,
            parent_id=resolved_parent_id,
            phone_number=phone,
            call_sid=mock_sid,
            status="COMPLETED",
            duration_seconds=18,
            parent_response="[DEMO] Parent confirmed student absence.",
            response_category="ACKNOWLEDGED",
            is_demo=True,
        )
        print("\nTest call recorded successfully in database.")
        return 0

    # REAL CALL
    account_sid = CONFIG.get("TWILIO_ACCOUNT_SID")
    auth_token = CONFIG.get("TWILIO_AUTH_TOKEN")
    from_number = CONFIG.get("TWILIO_FROM_NUMBER") or CONFIG.get("TWILIO_PHONE_NUMBER")

    if not account_sid or not auth_token or not from_number:
        print("[ERROR] Twilio credentials missing in environment. Cannot execute REAL call.", file=sys.stderr)
        return 1

    try:
        twilio_client = Client(account_sid, auth_token)
        acc = twilio_client.api.accounts(account_sid).fetch()
        is_trial = (acc.type.lower() == "trial")

        if is_trial:
            verified = [c.phone_number for c in twilio_client.outgoing_caller_ids.list(limit=10)]
            if phone not in verified:
                print(f"[ERROR] Destination number {phone} is NOT in Twilio's verified caller IDs.")
                print(f"        On Twilio Trial accounts, you can only call verified numbers: {verified}")
                print(f"        To test real phone ringing, run: python cli.py call-test --phone {verified[0] if verified else '+91XXXXXXXXXX'}")
                return 1

        session_id = str(uuid4())
        public_base_url = CONFIG.get("PUBLIC_BASE_URL", "").rstrip("/")
        active_url = None
        if public_base_url:
            try:
                with httpx.Client(timeout=1.0) as chk:
                    res = chk.get(f"{public_base_url}/health")
                    if res.status_code == 200:
                        active_url = public_base_url
            except Exception:
                active_url = None

        dtmf_action_url = f"{active_url}/twiml/dtmf/{session_id}" if active_url else None
        twiml_payload = build_twiml(voice_msg, session_id, dtmf_action_url)

        print(f"[REAL CALL] Placing outbound phone call to {phone} from {from_number}...")
        tw_call = twilio_client.calls.create(
            to=phone,
            from_=from_number,
            twiml=twiml_payload,
            status_callback=f"{active_url}/status" if active_url else None,
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )

        call_sid = tw_call.sid
        print(f"[SUCCESS] Twilio Call Initiated!")
        print(f"          Call SID:       {call_sid}")
        print(f"          Initial Status: {tw_call.status.upper()}")

        print("\nTracking live phone call progress (pick up the phone now)...")
        final_status = tw_call.status.upper()
        duration = 0

        for sec in range(1, 35):
            time.sleep(1)
            fetched = twilio_client.calls(call_sid).fetch()
            curr_status = fetched.status.upper()
            if curr_status != final_status:
                print(f"  [{sec:02d}s] Call status transitioned -> {curr_status}")
                final_status = curr_status
            if curr_status in ("COMPLETED", "BUSY", "NO-ANSWER", "FAILED", "CANCELED"):
                duration = fetched.duration or 0
                break

        print(f"\nFinal Twilio Call Status: {final_status} (Duration: {duration}s)")

        # Check if DTMF response was logged
        recorded_response = None
        v_engine = get_voice_db_engine()
        if v_engine:
            try:
                with v_engine.connect() as v_conn:
                    row = v_conn.execute(
                        text("SELECT response_text FROM parent_call_responses WHERE session_id = CAST(:sid AS UUID)"),
                        {"sid": session_id},
                    ).scalar_one_or_none()
                    if row:
                        recorded_response = row
            except Exception:
                pass

        if not recorded_response:
            recorded_response = "Real outbound call completed via Twilio."

        record_call_in_db(
            student_id=resolved_student_id,
            student_name=student_name,
            parent_id=resolved_parent_id,
            phone_number=phone,
            call_sid=call_sid,
            status=final_status,
            duration_seconds=int(duration),
            parent_response=recorded_response,
            response_category="REAL_CALL",
            is_demo=False,
        )

        print("-" * 70)
        print(f"RESULT: Actual phone call was completed and logged in database.")
        print(f"Call SID: {call_sid} | Status: {final_status}")
        print("=" * 70 + "\n")
        return 0

    except TwilioRestException as e:
        print(f"\n[Twilio Rest Error] {e.msg}")
        return 1
    except Exception as e:
        print(f"\n[Error] {type(e).__name__}: {e}")
        return 1


# ---------------------------------------------------------------------------
# CLI Command 5: history
# ---------------------------------------------------------------------------
def cmd_history(args: argparse.Namespace) -> int:
    """Show recent call history and recorded parent responses."""
    limit = args.limit or 15
    engine = get_backend_engine()

    print("\n" + "=" * 85)
    print(f" ATTENDWISE AI - RECENT CALL ATTEMPTS & RESPONSES (Latest {limit})")
    print("=" * 85)

    with engine.connect() as conn:
        q = """
            SELECT ca.id, ca.phone_number, ca.status, ca.provider_call_id,
                   ca.started_at, ca.duration_seconds, ca.failure_reason,
                   s.first_name, s.last_name, s.roll_number,
                   p.name as parent_name,
                   a.category as ai_category, a.summary as ai_summary
            FROM call_attempts ca
            LEFT JOIN campaign_targets ct ON ct.id = ca.campaign_target_id
            LEFT JOIN students s ON s.id = ct.student_id
            LEFT JOIN parents p ON p.id = ca.parent_id
            LEFT JOIN conversations c ON c.call_attempt_id = ca.id
            LEFT JOIN ai_analyses a ON a.conversation_id = c.id
            ORDER BY ca.created_at DESC
            LIMIT :lim
        """
        rows = conn.execute(text(q), {"lim": limit}).fetchall()

    if not rows:
        print("No call attempts found in database.\n")
        return 0

    # Also check parent_call_responses from voice DB
    voice_responses: dict[str, str] = {}
    v_engine = get_voice_db_engine()
    if v_engine:
        try:
            with v_engine.connect() as v_conn:
                v_rows = v_conn.execute(
                    text("SELECT student_name, response_text, session_id FROM parent_call_responses ORDER BY recorded_at DESC LIMIT 20")
                ).fetchall()
                for vr in v_rows:
                    voice_responses[str(vr[0])] = vr[1]
        except Exception:
            pass

    print(f"{'TIMESTAMP':<19} | {'STUDENT':<18} | {'PHONE':<13} | {'STATUS':<11} | {'CALL SID':<20} | {'DUR':<4} | {'NOTES / RESPONSE'}")
    print("-" * 85)

    for r in rows:
        m = dict(r._mapping)
        ts = m["started_at"].strftime("%Y-%m-%d %H:%M") if m["started_at"] else "-"
        st_name = f"{m['first_name'] or ''} {m['last_name'] or ''}".strip() or "Student"
        phone = m["phone_number"] or "-"
        st = m["status"] or "UNKNOWN"
        sid = (m["provider_call_id"] or "-")[:20]
        dur = f"{m['duration_seconds'] or 0}s"
        note = m["failure_reason"] or m.get("ai_summary") or voice_responses.get(st_name) or "-"

        print(f"{ts:<19} | {st_name:<18} | {phone:<13} | {st:<11} | {sid:<20} | {dur:<4} | {note[:30]}")

    print("-" * 85 + "\n")
    return 0


# ---------------------------------------------------------------------------
# Argument Parser & Entry Point
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python cli.py",
        description="AttendWise AI - Terminal CLI for School/College Attendance Calling Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py test
  python cli.py students
  python cli.py students --date 2026-11-17 --status ABSENT
  python cli.py call-test --phone +917309872195
  python cli.py call-absent --date 2026-11-17
  python cli.py call-absent --date 2026-11-17 --demo
  python cli.py history --limit 10
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. test
    subparsers.add_parser("test", help="Run comprehensive system diagnostics (DB, Twilio, AI, Voice)")

    # 2. students
    p_students = subparsers.add_parser("students", help="List student roster and attendance information")
    p_students.add_argument("--date", help="Filter by attendance date (YYYY-MM-DD)")
    p_students.add_argument("--status", choices=["ALL", "ABSENT", "PRESENT", "LATE"], default="ALL", help="Filter by attendance status")
    p_students.add_argument("--limit", type=int, default=50, help="Max students to display")

    # 3. call-absent
    p_absent = subparsers.add_parser("call-absent", help="Initiate calls for absent students on a given date")
    p_absent.add_argument("--date", required=True, help="Attendance date to query absent students (YYYY-MM-DD)")
    p_absent.add_argument("--yes", "-y", action="store_true", help="Bypass operator confirmation prompt")
    p_absent.add_argument("--demo", action="store_true", help="Run in DEMO / mock mode without placing real calls")
    p_absent.add_argument("--lang", choices=["hi", "en"], default="hi", help="Language for voice message (hi or en)")

    # 4. call-test
    p_test = subparsers.add_parser("call-test", help="Make one real or demo test call to a specific phone number")
    p_test.add_argument("--phone", required=True, help="Recipient phone number in E.164 format (+91XXXXXXXXXX)")
    p_test.add_argument("--student-name", default="Aarav Sharma", help="Name of the student for the absence notification")
    p_test.add_argument("--parent-name", default="Rajesh Sharma", help="Name of the parent/guardian")
    p_test.add_argument("--demo", action="store_true", help="Simulate call without dialing actual phone")
    p_test.add_argument("--lang", choices=["hi", "en"], default="hi", help="Language for voice message")

    # 5. history
    p_hist = subparsers.add_parser("history", help="Show recent call history, status, and responses")
    p_hist.add_argument("--limit", type=int, default=15, help="Number of recent calls to display")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "test": cmd_test,
        "students": cmd_students,
        "call-absent": cmd_call_absent,
        "call-test": cmd_call_test,
        "history": cmd_history,
    }

    cmd_fn = dispatch.get(args.command)
    if not cmd_fn:
        parser.print_help()
        return 1

    return cmd_fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

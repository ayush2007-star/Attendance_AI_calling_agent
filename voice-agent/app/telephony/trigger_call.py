import argparse
import os
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

# Allow `python voice-agent/app/telephony/trigger_call.py` from the repository
# root without requiring a separately configured PYTHONPATH.
VOICE_AGENT_ROOT = Path(__file__).resolve().parents[2]
if str(VOICE_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(VOICE_AGENT_ROOT))

import httpx
from pydantic import ValidationError

from app.telephony.schemas import CallContext
from app.telephony.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Request one authorized attendance call from the voice service."
    )
    parser.add_argument("--campaign-target-id", type=UUID, required=True)
    parser.add_argument("--student-id", type=UUID, required=True)
    parser.add_argument("--student-name", required=True)
    parser.add_argument("--parent-name", required=True)
    parser.add_argument("--phone-number", required=True)
    parser.add_argument("--attendance-date", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--preferred-language",
        choices=("hi-IN", "en-IN"),
        default="hi-IN",
    )
    parser.add_argument(
        "--attendance-percentage",
        type=float,
        default=68.5,
        help="Current attendance percentage of the student.",
    )
    parser.add_argument(
        "--parent-contact-authorized",
        action="store_true",
        help="Confirm that this parent is authorized to receive the call.",
    )
    parser.add_argument(
        "--idempotency-key",
        default=str(uuid4()),
        help="Reuse the same key if retrying this call request.",
    )
    parser.add_argument(
        "--service-url",
        default=os.getenv("VOICE_SERVICE_URL", "http://127.0.0.1:8001"),
    )
    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    if not arguments.parent_contact_authorized:
        parser.error("--parent-contact-authorized is required")
    api_key = os.getenv("CALL_API_KEY") or get_settings().call_api_key
    if not api_key:
        parser.error(
            "Set CALL_API_KEY in voice-agent/.env or in the environment"
        )

    service_url = urlsplit(arguments.service_url)
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if not service_url.hostname or service_url.scheme not in {"http", "https"}:
        parser.error("Voice service URL must use HTTP or HTTPS")
    if service_url.scheme == "http" and service_url.hostname not in local_hosts:
        parser.error("Use HTTPS for non-local voice service URLs")
    if service_url.username or service_url.password:
        parser.error("Do not include credentials in the voice service URL")
    if not 16 <= len(arguments.idempotency_key) <= 128:
        parser.error("Idempotency key must be between 16 and 128 characters")

    try:
        context = CallContext(
            campaign_target_id=arguments.campaign_target_id,
            student_id=arguments.student_id,
            student_name=arguments.student_name,
            parent_name=arguments.parent_name,
            phone_number=arguments.phone_number,
            attendance_date=arguments.attendance_date,
            preferred_language=arguments.preferred_language,
            attendance_percentage=arguments.attendance_percentage,
        )
    except ValidationError as error:
        parser.error(str(error))

    request_body = {
        "context": context.model_dump(mode="json"),
        "parent_contact_authorized": True,
    }

    try:
        response = httpx.post(
            f"{arguments.service_url.rstrip('/')}/calls",
            headers={
                "X-API-Key": api_key,
                "Idempotency-Key": arguments.idempotency_key,
            },
            json=request_body,
            timeout=httpx.Timeout(20, connect=5),
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        print(
            f"Call request rejected ({error.response.status_code}): "
            f"{error.response.text}",
            file=sys.stderr,
        )
        return 1
    except httpx.RequestError as error:
        print(f"Could not reach the voice service: {error}", file=sys.stderr)
        return 1

    try:
        result = response.json()
        session_id = UUID(result["session_id"])
        provider_call_id = result["provider_call_id"]
        call_status = result["status"]
    except (ValueError, KeyError, TypeError) as error:
        print(f"Voice service returned an invalid response: {error}", file=sys.stderr)
        return 1

    print(
        f"Call queued. Session ID: {session_id}; "
        f"Twilio call ID: {provider_call_id}; status: {call_status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

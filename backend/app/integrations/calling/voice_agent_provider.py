import logging
from datetime import datetime, timezone
from typing import Any
import httpx

from app.core.config import settings
from app.integrations.calling.base import CallRequest, ProviderCallResult

logger = logging.getLogger("attendance_backend.calling.voice_agent")


class VoiceAgentCallingProvider:
    """
    Production calling provider that integrates with the standalone voice-agent service.
    Sends authenticated server-to-server requests with idempotency keys and structured context.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = (base_url or settings.voice_agent_base_url).rstrip("/")
        self.api_key = api_key or settings.voice_agent_api_key
        self.timeout = timeout_seconds

    def start_call(self, request: CallRequest) -> ProviderCallResult:
        if not settings.real_calls_enabled:
            raise RuntimeError(
                "Real phone calling is disabled by configuration (REAL_CALLS_ENABLED=false). "
                "Use the demo mock provider or enable real calls with authorized test numbers."
            )
        if not settings.external_ai_processing_approved:
            raise RuntimeError(
                "External AI processing is not approved (EXTERNAL_AI_PROCESSING_APPROVED=false)."
            )

        context_data = request.context or {}
        phone_number = request.phone_number.strip()
        if not phone_number.startswith("+"):
            raise ValueError(f"Phone number must be E.164 formatted (+...): {phone_number}")

        # Structured payload matching voice-agent StartCallRequest
        payload = {
            "context": {
                "campaign_target_id": str(context_data.get("campaign_target_id", request.attempt_id)),
                "student_id": str(context_data.get("student_id", request.attempt_id)),
                "student_name": context_data.get("student_name", "Student"),
                "parent_name": context_data.get("parent_name", "Guardian"),
                "phone_number": phone_number,
                "attendance_date": str(context_data.get("attendance_date", datetime.now().date())),
                "preferred_language": context_data.get("preferred_language", "hi-IN"),
                "attendance_percentage": float(context_data.get("attendance_percentage", 0.0)),
                "threshold": float(context_data.get("threshold", 75.0)),
                "student_code": str(context_data.get("student_code", "")),
            },
            "parent_contact_authorized": True,
        }

        idempotency_key = f"backend-call-attempt-{request.attempt_id}"
        headers = {
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        url = f"{self.base_url}/calls"
        logger.info(
            "Dispatching call attempt %s to voice-agent at %s for %s",
            request.attempt_id,
            url,
            phone_number,
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                if response.status_code == 401:
                    raise RuntimeError("Voice agent service rejected authentication (invalid CALL_API_KEY)")
                if response.status_code == 403:
                    raise RuntimeError(f"Voice agent service rejected call: {response.text}")
                if response.status_code == 503:
                    raise RuntimeError(f"Voice agent service unavailable or not configured: {response.text}")
                response.raise_for_status()

                data = response.json()
                provider_call_id = data.get("provider_call_id") or data.get("session_id")
                call_status = data.get("status", "QUEUED")

                # Map initial provider status to valid backend transition (QUEUED -> RINGING)
                normalized_status = "RINGING" if call_status in ("QUEUED", "RINGING") else call_status

                return ProviderCallResult(
                    provider_call_id=str(provider_call_id),
                    status=normalized_status,
                    started_at=datetime.now(timezone.utc),
                )
        except httpx.ConnectError as err:
            logger.error("Could not connect to voice agent server at %s: %s", url, err)
            raise RuntimeError(
                f"Voice agent service is not running or unreachable at {self.base_url}. "
                "Ensure voice-agent server is running on port 8001 (run_server.ps1)."
            ) from err
        except httpx.HTTPStatusError as err:
            logger.error("Voice agent returned error %s: %s", err.response.status_code, err.response.text)
            raise RuntimeError(f"Voice agent call dispatch failed: {err.response.text}") from err
        except Exception as err:
            logger.exception("Unexpected error communicating with voice agent: %s", err)
            raise RuntimeError(f"Voice agent dispatch failed: {err}") from err

    def end_call(self, provider_call_id: str) -> None:
        logger.info("Requesting termination of provider call %s", provider_call_id)

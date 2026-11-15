import logging
from typing import Any
from uuid import UUID

import requests

from app.contracts.call_context import CallContext
from app.telephony.settings import get_settings

logger = logging.getLogger("attendance_voice.backend_client")


class BackendClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.backend_base_url).rstrip("/")
        self.api_key = api_key or settings.call_api_key
        self.access_token = None

    def login(self, username: str, password: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            data={
                "username": username,
                "password": password,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        self.access_token = data["access_token"]
        return self.access_token

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            return {}
        return {
            "Authorization": f"Bearer {self.access_token}"
        }

    def _callback_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def get(self, path: str) -> dict:
        response = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_call_context(self, campaign_target_id: UUID) -> CallContext:
        payload = self.get(
            f"/api/v1/calls/targets/{campaign_target_id}/context"
        )
        return CallContext.model_validate(payload)

    def health_check(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False

    def notify_call_status(self, provider_call_id: str, new_status: str) -> bool:
        """Inform backend of call progress events (ringing, answered, failed, completed)."""
        url = f"{self.base_url}/api/v1/calls/attempts/{provider_call_id}/status"
        try:
            response = requests.post(
                url,
                json={"status": new_status},
                headers=self._callback_headers(),
                timeout=5,
            )
            return response.status_code == 200
        except Exception as err:
            logger.warning("Could not notify backend of call status %s for %s: %s", new_status, provider_call_id, err)
            return False

    def notify_call_completed(self, payload: dict[str, Any]) -> bool:
        """Post complete call transcripts, category, and follow-up data to backend source of truth."""
        url = f"{self.base_url}/api/v1/calls/callback"
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._callback_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                logger.info("Successfully synchronized call completion to backend for %s", payload.get("provider_call_id"))
                return True
            logger.warning("Backend rejected call completion callback (%s): %s", response.status_code, response.text)
            return False
        except Exception as err:
            logger.warning("Failed to deliver call completion to backend: %s", err)
            return False

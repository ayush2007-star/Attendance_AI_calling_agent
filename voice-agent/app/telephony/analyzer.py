import logging
import re
from typing import Any

import httpx

from app.telephony.prompts import build_response_analyzer_system_prompt
from app.telephony.schemas import StructuredAnalysis
from app.telephony.settings import TelephonySettings


logger = logging.getLogger("attendance_voice.analyzer")


class ResponseAnalyzer:
    """Analyzes completed conversation transcript to classify parent response."""

    def __init__(self, settings: TelephonySettings) -> None:
        self.settings = settings

    async def analyze(
        self,
        transcript: str,
        student_name: str,
    ) -> StructuredAnalysis:
        if not transcript or not transcript.strip():
            return StructuredAnalysis(
                response_category="OTHER",
                reason_summary="No spoken conversation recorded",
                followup_required=True,
            )

        endpoint = f"{self.settings.groq_base_url.rstrip('/')}/chat/completions"
        system_content = build_response_analyzer_system_prompt()

        payload = {
            "model": self.settings.groq_model,
            "temperature": 0.1,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_content},
                {
                    "role": "user",
                    "content": f"Student Name: {student_name}\n\nCall Transcript:\n{transcript[:3000]}",
                },
            ],
        }

        timeout = httpx.Timeout(12, connect=5)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
                    json=payload,
                )
                response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"]
            return StructuredAnalysis.model_validate_json(content)
        except Exception as e:
            logger.warning(
                "LLM analyzer failed, falling back to rule-based classification: %s",
                e,
            )
            return self._fallback_rule_based(transcript)

    @staticmethod
    def _fallback_rule_based(transcript: str) -> StructuredAnalysis:
        lower = transcript.casefold()

        # Medical reasons
        if any(
            w in lower
            for w in [
                "bimar",
                "bukhar",
                "tabiyat",
                "ill",
                "sick",
                "fever",
                "hospital",
                "doctor",
                "dawa",
            ]
        ):
            return StructuredAnalysis(
                response_category="MEDICAL_REASON",
                reason_summary="Student was unwell or sick",
                followup_required=False,
            )

        # Callback requested
        if any(
            w in lower
            for w in [
                "baad me",
                "shaam ko",
                "call karna",
                "call me",
                "busy",
                "khet me",
                "monday",
                "kal baat",
            ]
        ):
            return StructuredAnalysis(
                response_category="CALLBACK_REQUESTED",
                reason_summary="Parent requested callback at a later time",
                followup_required=True,
            )

        # Leave related
        if any(
            w in lower
            for w in [
                "shadi",
                "shaadi",
                "gav",
                "gaon",
                "function",
                "leave",
                "chhutti",
                "kaam tha",
            ]
        ):
            return StructuredAnalysis(
                response_category="LEAVE_RELATED",
                reason_summary="Family function or travel to hometown",
                followup_required=False,
            )

        # Wrong number
        if any(
            w in lower
            for w in [
                "galat number",
                "wrong number",
                "nahi janta",
                "kisi aur ka",
            ]
        ):
            return StructuredAnalysis(
                response_category="WRONG_NUMBER",
                reason_summary="Wrong contact number",
                followup_required=True,
            )

        # Will attend
        if any(
            w in lower
            for w in [
                "kal aayega",
                "kal se jayega",
                "bhej denge",
                "attendance",
                "theek hai",
            ]
        ):
            return StructuredAnalysis(
                response_category="WILL_ATTEND",
                reason_summary="Parent acknowledged and will send student",
                followup_required=False,
            )

        return StructuredAnalysis(
            response_category="OTHER",
            reason_summary=transcript[:120].strip(),
            followup_required=False,
        )

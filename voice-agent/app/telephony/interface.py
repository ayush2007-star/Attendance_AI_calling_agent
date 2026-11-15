"""
Formal protocols and interfaces for telephony components.
Enables provider independence (TTS, STT, LLM, Store).
"""

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class TTSProvider(Protocol):
    """Interface for text-to-speech audio providers."""

    def audio_chunks(
        self,
        text: str,
        language: str = "hi-IN",
    ) -> AsyncIterator[bytes]:
        """Yield raw 8kHz mono mu-law audio chunks suitable for telephony."""
        ...


@runtime_checkable
class STTProvider(Protocol):
    """Interface for streaming speech-to-text providers."""

    async def open_stream(self) -> Any:
        """Open a streaming STT websocket or connection."""
        ...


@runtime_checkable
class GuardianVerifierProtocol(Protocol):
    """Interface for verifying caller identity."""

    async def is_guardian(
        self, utterance: str, parent_name: str | None = None
    ) -> bool:
        """Return True if speaker confirms or identifies as student's parent/guardian."""
        ...


@runtime_checkable
class AttendanceResponderProtocol(Protocol):
    """Interface for multi-turn dialogue generation."""

    async def respond(
        self,
        utterance: str,
        context: Any,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a short, natural, empathetic response for the parent."""
        ...


@runtime_checkable
class ResponseAnalyzerProtocol(Protocol):
    """Interface for post-call conversation classification."""

    async def analyze(
        self,
        transcript: str,
        student_name: str,
    ) -> dict[str, Any]:
        """Extract structured classification (category, summary, followup_required)."""
        ...

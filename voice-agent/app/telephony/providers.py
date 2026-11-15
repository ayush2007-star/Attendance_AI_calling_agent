import base64
import io
import json
import logging
import re
from collections.abc import AsyncIterator
from urllib.parse import urlencode
from uuid import uuid4

import av
import edge_tts
import httpx
import numpy as np
from websockets.asyncio.client import connect

from app.telephony.prompts import (
    build_attendance_responder_system_prompt,
    build_guardian_verifier_system_prompt,
)
from app.telephony.schemas import GuardianCheck
from app.telephony.settings import TelephonySettings


logger = logging.getLogger("attendance_voice.providers")

# Standard G.711 mu-law compression lookup table for 16-bit signed PCM
_BIAS = 0x84
_CLIP = 32635


def _linear_to_mulaw_sample(sample: int) -> int:
    sign = 0
    if sample < 0:
        sample = -sample
        sign = 0x80
    if sample > _CLIP:
        sample = _CLIP
    sample += _BIAS
    exponent = 7
    mask = 0x4000
    while exponent > 0 and (sample & mask) == 0:
        exponent -= 1
        mask >>= 1
    mantissa = (sample >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


_LINEAR_TO_MULAW_TABLE = bytes(
    _linear_to_mulaw_sample(i) for i in range(-32768, 32768)
)


def pcm16_to_mulaw(pcm_bytes: bytes) -> bytes:
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    indices = samples.astype(np.int32) + 32768
    table_arr = np.frombuffer(_LINEAR_TO_MULAW_TABLE, dtype=np.uint8)
    return table_arr[indices].tobytes()


def clean_text_for_speech(text: str, language: str = "hi-IN") -> str:
    """Preprocess text to ensure numbers and abbreviations sound natural in Hindi."""
    clean = text.strip()
    if language.casefold().startswith("hi"):
        clean = re.sub(r"(\d+)\s*%", r"\1 प्रतिशत", clean)
        clean = clean.replace("BBS", "बीबीएस")
    return clean


class DeepgramSTT:
    def __init__(self, settings: TelephonySettings) -> None:
        self.settings = settings

    async def open_stream(self):
        query = urlencode(
            {
                "model": self.settings.deepgram_model,
                "language": self.settings.deepgram_language,
                "encoding": "mulaw",
                "sample_rate": 8000,
                "channels": 1,
                "interim_results": "true",
                "endpointing": 400,
                "vad_events": "true",
            }
        )
        return await connect(
            f"wss://api.deepgram.com/v1/listen?{query}",
            additional_headers={
                "Authorization": f"Token {self.settings.deepgram_api_key}"
            },
            open_timeout=10,
            close_timeout=3,
            max_size=1_048_576,
        )


class GroqGuardianVerifier:
    def __init__(self, settings: TelephonySettings) -> None:
        self.settings = settings

    async def is_guardian(
        self, utterance: str, parent_name: str | None = None
    ) -> bool:
        endpoint = (
            f"{self.settings.groq_base_url.rstrip('/')}/chat/completions"
        )
        system_content = build_guardian_verifier_system_prompt(parent_name)
        payload = {
            "model": self.settings.groq_model,
            "temperature": 0.1,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": system_content,
                },
                {
                    "role": "user",
                    "content": f"Parent's spoken answer: {utterance[:1000]}",
                },
            ],
        }
        timeout = httpx.Timeout(12, connect=5)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.settings.groq_api_key}"
                },
                json=payload,
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise RuntimeError("Groq returned an invalid guardian check")
        return GuardianCheck.model_validate_json(content).guardian_confirmed


class GroqAttendanceResponder:
    def __init__(self, settings: TelephonySettings) -> None:
        self.settings = settings

    async def respond(
        self,
        utterance: str,
        language: str,
        school_name: str,
        student_name: str = "Student",
        attendance_date: str = "today",
        attendance_pct: float = 0.0,
        threshold: float = 75.0,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> str:
        endpoint = (
            f"{self.settings.groq_base_url.rstrip('/')}/chat/completions"
        )
        system_content = build_attendance_responder_system_prompt(
            school_name=school_name,
            student_name=student_name,
            attendance_date=attendance_date,
            attendance_pct=attendance_pct,
            threshold=threshold,
            language=language,
            gender=self.settings.assistant_gender,
            persona=self.settings.voice_persona,
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_content}
        ]

        if conversation_history:
            messages.extend(conversation_history[-6:])

        messages.append(
            {"role": "user", "content": f"Parent's response: {utterance[:1000]}"}
        )

        payload = {
            "model": self.settings.groq_model,
            "temperature": self.settings.groq_temperature,
            "max_tokens": 512,
            "messages": messages,
        }
        timeout = httpx.Timeout(12, connect=5)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.settings.groq_api_key}"
                },
                json=payload,
            )
            response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Groq returned an empty attendance response")

        clean = content.strip().strip('"').strip("'")
        sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", clean) if s.strip()]
        if not sentences:
            if language.casefold().startswith("hi"):
                return "जी ठीक है, हमने आपकी बात नोट कर ली है और कॉलेज को बता देंगे। धन्यवाद।"
            return "Thank you. I have noted this down for the college team."

        reply = " ".join(sentences[:2])
        if not reply.endswith((".", "!", "?", "।")):
            reply += "।" if language.casefold().startswith("hi") else "."
        return reply[:500]


class EdgeTTS:
    def __init__(self, settings: TelephonySettings) -> None:
        self.settings = settings

    async def audio_chunks(
        self,
        text: str,
        language: str = "hi-IN",
    ) -> AsyncIterator[bytes]:
        if language.casefold().startswith("hi"):
            voice = getattr(self.settings, "edge_voice_hi", "hi-IN-SwaraNeural")
        else:
            voice = getattr(self.settings, "edge_voice_en", "en-IN-NeerjaNeural")

        rate = getattr(self.settings, "edge_voice_rate", "+25%")
        pitch = getattr(self.settings, "edge_voice_pitch", "+0Hz")
        spoken_text = clean_text_for_speech(text, language)

        communicate = edge_tts.Communicate(spoken_text, voice=voice, rate=rate, pitch=pitch)
        mp3_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_data.extend(chunk["data"])

        if not mp3_data:
            raise RuntimeError("EdgeTTS returned no audio")

        input_container = av.open(io.BytesIO(mp3_data), format="mp3")
        try:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=8000)
            for frame in input_container.decode(audio=0):
                for resampled_frame in resampler.resample(frame):
                    mulaw = pcm16_to_mulaw(resampled_frame.to_ndarray().tobytes())
                    if mulaw:
                        yield mulaw
        finally:
            input_container.close()


class CartesiaTTS:
    def __init__(self, settings: TelephonySettings) -> None:
        self.settings = settings

    async def audio_chunks(
        self,
        text: str,
        language: str = "hi-IN",
    ) -> AsyncIterator[bytes]:
        if not self.settings.cartesia_voice_id:
            raise RuntimeError("CARTESIA_VOICE_ID is required")

        url = (
            "wss://api.cartesia.ai/tts/websocket?"
            f"cartesia_version={self.settings.cartesia_version}"
        )
        request = {
            "model_id": self.settings.cartesia_model,
            "transcript": text,
            "voice": {"id": self.settings.cartesia_voice_id},
            "output_format": {
                "container": "raw",
                "encoding": "pcm_mulaw",
                "sample_rate": 8000,
            },
            "language": language,
            "context_id": str(uuid4()),
            "continue": False,
            "max_buffer_delay_ms": 0,
        }
        received_audio = False

        async with connect(
            url,
            additional_headers={
                "X-Api-Key": self.settings.cartesia_api_key
            },
            open_timeout=10,
            close_timeout=3,
            max_size=1_048_576,
        ) as socket:
            await socket.send(json.dumps(request, ensure_ascii=False))
            async for message in socket:
                if isinstance(message, bytes):
                    raise RuntimeError(
                        "Cartesia returned an unexpected binary message"
                    )

                event = json.loads(message)
                event_type = event.get("type")
                if event_type == "chunk":
                    audio_data = event.get("data")
                    if not isinstance(audio_data, str):
                        raise RuntimeError("Cartesia returned an invalid audio chunk")
                    received_audio = True
                    yield base64.b64decode(audio_data, validate=True)
                elif event_type == "done":
                    break
                elif event_type == "error":
                    raise RuntimeError("Cartesia TTS request failed")

        if not received_audio:
            raise RuntimeError("Cartesia returned no audio")


class DeepgramTTS:
    def __init__(self, settings: TelephonySettings) -> None:
        self.settings = settings

    async def audio_chunks(
        self,
        text: str,
        language: str = "hi-IN",
    ) -> AsyncIterator[bytes]:
        if not self.settings.deepgram_api_key:
            raise RuntimeError("DEEPGRAM_API_KEY is required for Deepgram TTS")

        model = "aura-asteria-en"
        url = (
            f"https://api.deepgram.com/v1/speak?model={model}"
            "&encoding=mulaw&sample_rate=8000"
        )
        headers = {
            "Authorization": f"Token {self.settings.deepgram_api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(15, connect=5)
        received_audio = False
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                url,
                headers=headers,
                json={"text": text},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        received_audio = True
                        yield chunk

        if not received_audio:
            raise RuntimeError("Deepgram returned no audio")


def get_tts_provider(settings: TelephonySettings):
    provider = getattr(settings, "tts_provider", "auto").casefold()
    if provider == "cartesia":
        return CartesiaTTS(settings)
    if provider == "deepgram":
        return DeepgramTTS(settings)
    if provider == "edge":
        return EdgeTTS(settings)
    # auto mode:
    if settings.cartesia_api_key and settings.cartesia_voice_id:
        return CartesiaTTS(settings)
    if settings.deepgram_api_key:
        return DeepgramTTS(settings)
    return EdgeTTS(settings)

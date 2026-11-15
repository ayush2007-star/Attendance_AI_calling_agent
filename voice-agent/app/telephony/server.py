import asyncio
import base64
import hashlib
import hmac
import html
import json
import logging
import re
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Support Uvicorn imports from the repository root as well as direct module
# imports when this service is launched from its own directory.
VOICE_AGENT_ROOT = Path(__file__).resolve().parents[2]
if str(VOICE_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(VOICE_AGENT_ROOT))

import requests
from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import Response
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.telephony.analyzer import ResponseAnalyzer
from app.telephony.dialog_manager import DialogManager
from app.telephony.providers import (
    DeepgramSTT,
    GroqAttendanceResponder,
    GroqGuardianVerifier,
    get_tts_provider,
)
from app.telephony.schemas import CallContext, StartCallRequest, StartCallResponse
from app.telephony.settings import TelephonySettings, get_settings
from app.telephony.store import CallSession, CallStore
from app.integrations.backend_client import BackendClient


logger = logging.getLogger("attendance_voice")
MEDIA_FRAME_BYTES = 160
_E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def twilio_signature(
    auth_token: str,
    url: str,
    parameters: dict[str, str],
) -> str:
    data = url + "".join(
        key + parameters[key] for key in sorted(parameters)
    )
    digest = hmac.new(
        auth_token.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def validate_twilio_signature(
    auth_token: str,
    url: str,
    parameters: dict[str, str],
    signature: str | None,
) -> bool:
    if not auth_token or not signature:
        return False
    expected = twilio_signature(auth_token, url, parameters)
    return hmac.compare_digest(expected, signature)


def build_twiml(public_base_url: str, session: CallSession) -> str:
    ws_base = public_base_url.rstrip("/")
    if ws_base.startswith("https://"):
        ws_base = "wss://" + ws_base[len("https://"):]
    else:
        raise ValueError("PUBLIC_BASE_URL must use HTTPS")

    stream_url = html.escape(f"{ws_base}/media-stream", quote=True)
    session_id = html.escape(session.session_id, quote=True)
    stream_token = html.escape(session.stream_token, quote=True)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Connect><Stream "
        f'url="{stream_url}">'
        f'<Parameter name="session_id" value="{session_id}"/>'
        f'<Parameter name="stream_token" value="{stream_token}"/>'
        "</Stream></Connect><Hangup/></Response>"
    )


def external_request_url(request: Request, public_base_url: str) -> str:
    url = f"{public_base_url.rstrip('/')}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    return url


async def form_string_values(request: Request) -> dict[str, str]:
    form = await request.form()
    parameters: dict[str, str] = {}
    for key, value in form.multi_items():
        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unexpected webhook form value",
            )
        parameters[key] = value
    return parameters


async def require_valid_twilio_request(
    request: Request,
    settings: TelephonySettings,
) -> dict[str, str]:
    parameters = await form_string_values(request)
    signature = request.headers.get("X-Twilio-Signature")
    request_url = external_request_url(request, settings.public_base_url)
    if not validate_twilio_signature(
        settings.twilio_auth_token,
        request_url,
        parameters,
        signature,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature",
        )
    return parameters


def ensure_service_configured(settings: TelephonySettings) -> None:
    if not settings.real_calls_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Real calls are disabled",
        )
    if not settings.external_ai_processing_approved:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External AI processing has not been enabled",
        )
    required = {
        "PUBLIC_BASE_URL": settings.public_base_url,
        "CALL_API_KEY": settings.call_api_key,
        "DATABASE_URL": settings.database_url,
        "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
        "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
        "TWILIO_FROM_NUMBER": settings.twilio_from_number,
        "DEEPGRAM_API_KEY": settings.deepgram_api_key,
        "GROQ_API_KEY": settings.groq_api_key,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Missing required settings: {', '.join(missing)}",
        )
    if not settings.public_base_url.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PUBLIC_BASE_URL must use HTTPS",
        )
    if not _E164_PATTERN.fullmatch(settings.twilio_from_number):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TWILIO_FROM_NUMBER must be in E.164 format",
        )


def create_app(settings: TelephonySettings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    store = CallStore(app_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        cleanup_task: asyncio.Task[None] | None = None
        if app_settings.database_url:
            await asyncio.to_thread(store.initialize)
            await asyncio.to_thread(store.expire_stale_sessions)

            async def clean_expired_sessions() -> None:
                while True:
                    await asyncio.sleep(300)
                    await asyncio.to_thread(store.expire_stale_sessions)

            cleanup_task = asyncio.create_task(clean_expired_sessions())
        try:
            yield
        finally:
            if cleanup_task:
                cleanup_task.cancel()
                await asyncio.gather(cleanup_task, return_exceptions=True)
            await asyncio.to_thread(store.dispose)

    app = FastAPI(
        title="Attendance Voice Calls",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.store = store

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/calls",
        response_model=StartCallResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def start_call(
        data: StartCallRequest,
        idempotency_key: str = Header(
            alias="Idempotency-Key",
            min_length=16,
            max_length=128,
        ),
        api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> StartCallResponse:
        ensure_service_configured(app_settings)
        if not api_key or not hmac.compare_digest(
            api_key,
            app_settings.call_api_key,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        if not data.parent_contact_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Parent contact authorization is required",
            )

        existing = await asyncio.to_thread(
            store.find_by_idempotency_key,
            idempotency_key,
        )
        if existing is not None:
            if existing.call_sid:
                return StartCallResponse(
                    session_id=uuid.UUID(existing.session_id),
                    provider_call_id=existing.call_sid,
                    status=existing.status,
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This idempotency key already has a pending call",
            )

        session_id = str(uuid.uuid4())
        stream_token = uuid.uuid4().hex + uuid.uuid4().hex
        context = data.context.model_dump(mode="json")
        inserted = await asyncio.to_thread(
            store.create_session,
            session_id,
            idempotency_key,
            stream_token,
            context,
        )
        if not inserted:
            existing = await asyncio.to_thread(
                store.find_by_idempotency_key,
                idempotency_key,
            )
            if existing and existing.call_sid:
                return StartCallResponse(
                    session_id=uuid.UUID(existing.session_id),
                    provider_call_id=existing.call_sid,
                    status=existing.status,
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This call request was already submitted",
            )

        callback_base = app_settings.public_base_url.rstrip("/")
        call_url = f"{callback_base}/twiml/{session_id}"
        callback_url = f"{callback_base}/status"
        try:
            twilio_client = Client(
                app_settings.twilio_account_sid,
                app_settings.twilio_auth_token,
            )
            twilio_call = await asyncio.to_thread(
                twilio_client.calls.create,
                to=data.context.phone_number,
                from_=app_settings.twilio_from_number,
                url=call_url,
                method="POST",
                status_callback=callback_url,
                status_callback_method="POST",
                status_callback_event=[
                    "initiated",
                    "ringing",
                    "answered",
                    "completed",
                ],
            )
            provider_call_id = twilio_call.sid
            if (
                not isinstance(provider_call_id, str)
                or not provider_call_id.startswith("CA")
            ):
                raise ValueError("Twilio did not return a call SID")
        except (
            TwilioRestException,
            requests.RequestException,
            ValueError,
        ):
            logger.exception("Twilio could not start call session %s", session_id)
            await asyncio.to_thread(store.update_status_by_session, session_id, "FAILED")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Twilio could not start the call",
            ) from None

        await asyncio.to_thread(
            store.bind_call_sid,
            session_id,
            provider_call_id,
        )
        return StartCallResponse(
            session_id=uuid.UUID(session_id),
            provider_call_id=provider_call_id,
            status="QUEUED",
        )

    @app.post("/twiml/{session_id}")
    async def twiml(session_id: str, request: Request) -> Response:
        ensure_service_configured(app_settings)
        parameters = await require_valid_twilio_request(request, app_settings)
        call_sid = parameters.get("CallSid", "")
        session = await asyncio.to_thread(store.get_session, session_id)
        if not session or not call_sid:
            raise HTTPException(status_code=404, detail="Call session not found")
        if not await asyncio.to_thread(
            store.bind_call_sid,
            session_id,
            call_sid,
        ):
            raise HTTPException(status_code=409, detail="Call session mismatch")
        session = await asyncio.to_thread(store.get_session, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Call session expired")
        return Response(
            content=build_twiml(app_settings.public_base_url, session),
            media_type="application/xml",
        )

    @app.post("/status")
    async def call_status(request: Request) -> Response:
        parameters = await require_valid_twilio_request(request, app_settings)
        call_sid = parameters.get("CallSid")
        call_status_value = parameters.get("CallStatus")
        if call_sid and call_status_value:
            await asyncio.to_thread(
                store.update_status,
                call_sid,
                call_status_value,
            )
            # If call ended without media stream (busy, no-answer, failed, canceled), notify backend
            lower_status = call_status_value.lower()
            if lower_status in ("busy", "no-answer", "failed", "canceled"):
                mapped = "BUSY" if lower_status == "busy" else "NO_ANSWER" if lower_status == "no-answer" else "FAILED"
                b_client = BackendClient(base_url=app_settings.backend_base_url, api_key=app_settings.call_api_key)
                await asyncio.to_thread(
                    b_client.notify_call_completed,
                    {
                        "provider_call_id": call_sid,
                        "status": mapped,
                        "duration_seconds": 0,
                        "failure_reason": f"Telephony provider reported {call_status_value}",
                        "turns": [],
                        "analysis": None,
                    },
                )
        return Response(
            content="<Response/>",
            media_type="application/xml",
        )

    @app.websocket("/media-stream")
    @app.websocket("/media")
    async def media_stream(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            await handle_media_stream(
                websocket,
                app_settings,
                store,
                DeepgramSTT(app_settings),
                GroqGuardianVerifier(app_settings),
                GroqAttendanceResponder(app_settings),
                get_tts_provider(app_settings),
                ResponseAnalyzer(app_settings),
            )
        except WebSocketDisconnect:
            logger.info("Twilio media stream disconnected")
        except Exception:
            logger.exception("Voice stream failed")
            try:
                await websocket.close(code=1011)
            except RuntimeError:
                pass

    return app


async def handle_media_stream(
    websocket: WebSocket,
    settings: TelephonySettings,
    store: CallStore,
    stt: DeepgramSTT,
    verifier: GroqGuardianVerifier,
    responder: GroqAttendanceResponder,
    tts: Any,
    analyzer: ResponseAnalyzer | None = None,
) -> None:
    connected = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    if connected.get("event") != "connected":
        await websocket.close(code=1002)
        return

    start = await asyncio.wait_for(websocket.receive_json(), timeout=10)
    if start.get("event") != "start":
        await websocket.close(code=1002)
        return

    start_data = start.get("start", {})
    media_format = start_data.get("mediaFormat", {})
    if (
        media_format.get("encoding") != "audio/x-mulaw"
        or media_format.get("sampleRate") != 8000
    ):
        await websocket.close(code=1003)
        return

    custom_parameters = start_data.get("customParameters", {})
    session_id = custom_parameters.get("session_id")
    supplied_token = custom_parameters.get("stream_token")
    session = await asyncio.to_thread(store.get_session, str(session_id))
    call_sid = start_data.get("callSid")
    if (
        session is None
        or not supplied_token
        or not hmac.compare_digest(session.stream_token, supplied_token)
        or session.call_sid != call_sid
    ):
        await websocket.close(code=1008)
        return

    context = CallContext.model_validate(session.context)
    stream_sid = start_data.get("streamSid")
    if not stream_sid:
        await websocket.close(code=1002)
        return

    audio_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    done_event = asyncio.Event()
    send_lock = asyncio.Lock()
    active_tts_task: asyncio.Task[None] | None = None

    dialog = DialogManager(
        context=context,
        settings=settings,
        verifier=verifier,
        responder=responder,
    )
    call_analyzer = analyzer or ResponseAnalyzer(settings)

    async def send_media(audio: bytes) -> None:
        for offset in range(0, len(audio), MEDIA_FRAME_BYTES):
            frame = audio[offset:offset + MEDIA_FRAME_BYTES]
            async with send_lock:
                await websocket.send_json(
                    {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": base64.b64encode(frame).decode("ascii")
                        },
                    }
                )

    async def speak(text: str) -> None:
        nonlocal active_tts_task

        async def send_tts_audio() -> None:
            language = (
                "en-IN"
                if context.preferred_language.casefold().startswith("en")
                else "hi-IN"
            )
            async for chunk in tts.audio_chunks(text, language):
                await send_media(chunk)

        active_tts_task = asyncio.create_task(send_tts_audio())
        try:
            result = await asyncio.gather(
                active_tts_task,
                return_exceptions=True,
            )
            error = result[0]
            if isinstance(error, BaseException) and not isinstance(
                error,
                asyncio.CancelledError,
            ):
                raise error
        finally:
            active_tts_task = None

    async def process_parent_turns() -> None:
        while not done_event.is_set():
            try:
                utterance = await audio_queue.get()
            except asyncio.CancelledError:
                break
            reply = await dialog.handle_parent_utterance(utterance)
            await speak(reply)
            if dialog.is_done:
                done_event.set()
                break

    async def read_stt_results(socket: Any) -> None:
        finalized_parts: list[str] = []
        async for message in socket:
            if isinstance(message, bytes):
                continue
            result = json.loads(message)
            if result.get("type") == "SpeechStarted":
                if active_tts_task and not active_tts_task.done():
                    active_tts_task.cancel()
                    async with send_lock:
                        await websocket.send_json(
                            {"event": "clear", "streamSid": stream_sid}
                        )
                continue
            if result.get("type") == "Error":
                raise RuntimeError("Deepgram transcription stream failed")

            alternatives = (
                result.get("channel", {}).get("alternatives", [{}])
            )
            transcript = alternatives[0].get("transcript", "").strip()
            if result.get("is_final") and transcript:
                finalized_parts.append(transcript)
            if result.get("speech_final"):
                utterance = " ".join(finalized_parts).strip()
                finalized_parts.clear()
                if not utterance and transcript:
                    utterance = transcript
                if utterance:
                    try:
                        audio_queue.put_nowait(utterance)
                    except asyncio.QueueFull as error:
                        raise RuntimeError(
                            "Too many parent speech turns in one call"
                        ) from error

    async def deepgram_keepalive(socket: Any) -> None:
        while True:
            await asyncio.sleep(5)
            await socket.send(json.dumps({"type": "KeepAlive"}))

    async with await stt.open_stream() as stt_socket:
        reader_task = asyncio.create_task(read_stt_results(stt_socket))
        agent_task = asyncio.create_task(process_parent_turns())
        keepalive_task = asyncio.create_task(deepgram_keepalive(stt_socket))
        
        # Start with natural greeting
        initial_greeting = dialog.initial_greeting()
        greeting_task = asyncio.create_task(speak(initial_greeting))

        tasks = (reader_task, agent_task, keepalive_task)
        deadline = asyncio.get_running_loop().time() + settings.max_call_seconds

        try:
            while not done_event.is_set():
                if asyncio.get_running_loop().time() >= deadline:
                    logger.warning("Call session %s reached its time limit", session_id)
                    break

                if greeting_task.done():
                    greeting_task.result()

                for task in tasks:
                    if task.done():
                        task.result()
                        raise RuntimeError("Voice provider task stopped unexpectedly")

                try:
                    event = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=0.5,
                    )
                except TimeoutError:
                    continue

                event_type = event.get("event")
                if event_type == "media":
                    payload = event.get("media", {}).get("payload", "")
                    try:
                        audio = base64.b64decode(payload, validate=True)
                    except ValueError as error:
                        raise RuntimeError("Twilio sent invalid audio data") from error
                    if len(audio) > 16_000:
                        raise RuntimeError("Twilio audio frame exceeded the limit")
                    await stt_socket.send(audio)
                elif event_type == "stop":
                    break
        finally:
            if not greeting_task.done():
                greeting_task.cancel()
            if active_tts_task and not active_tts_task.done():
                active_tts_task.cancel()
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(
                greeting_task,
                *tasks,
                return_exceptions=True,
            )

            # Analyze conversation and save structured response
            try:
                full_transcript = dialog.get_full_transcript()
                analysis = await call_analyzer.analyze(
                    transcript=full_transcript,
                    student_name=context.student_name,
                )
                summary = analysis.reason_summary or (
                    dialog.turns[-1].text if dialog.turns else "Call finished"
                )
                await asyncio.to_thread(
                    store.save_parent_response,
                    session.session_id,
                    str(context.student_id),
                    context.student_name,
                    summary,
                    analysis.response_category,
                    analysis.followup_required,
                    None,
                    full_transcript,
                )

                # Synchronize completed call data to main backend database
                b_client = BackendClient(base_url=settings.backend_base_url, api_key=settings.call_api_key)
                turns_payload = [
                    {
                        "speaker": t.speaker.upper(),
                        "text": t.text,
                        "confidence": 0.95,
                        "sequence_number": idx,
                    }
                    for idx, t in enumerate(dialog.turns, start=1)
                ]
                call_payload = {
                    "provider_call_id": session.call_sid or session.session_id,
                    "status": "COMPLETED",
                    "duration_seconds": max(5, int(len(dialog.turns) * 4)),
                    "language": context.preferred_language,
                    "turns": turns_payload,
                    "analysis": {
                        "category": analysis.response_category,
                        "summary": summary,
                        "followup_required": analysis.followup_required,
                        "callback_at": analysis.callback_at,
                        "model_name": f"{settings.groq_model} (Groq Voice Agent)",
                        "sentiment": analysis.parent_sentiment,
                    },
                    "is_demo": False,
                }
                await asyncio.to_thread(b_client.notify_call_completed, call_payload)
            except Exception as e:
                logger.warning("Could not complete post-call analysis or backend sync: %s", e)


app = create_app()

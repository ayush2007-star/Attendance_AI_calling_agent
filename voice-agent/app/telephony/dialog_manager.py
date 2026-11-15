import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.telephony.prompts import (
    get_attendance_query,
    get_closing_message,
    get_greeting,
    get_unclear_speech_message,
    get_wrong_person_message,
)
from app.telephony.providers import GroqAttendanceResponder, GroqGuardianVerifier
from app.telephony.schemas import CallContext
from app.telephony.settings import TelephonySettings


logger = logging.getLogger("attendance_voice.dialog")


@dataclass
class DialogTurn:
    speaker: str
    text: str


class DialogManager:
    """
    Manages multi-turn conversation flow between the voice agent
    and the student's parent/guardian.
    """

    def __init__(
        self,
        context: CallContext,
        settings: TelephonySettings,
        verifier: GroqGuardianVerifier,
        responder: GroqAttendanceResponder,
    ) -> None:
        self.context = context
        self.settings = settings
        self.verifier = verifier
        self.responder = responder

        self.phase: str = "greeting"  # greeting -> verify -> discuss -> closing -> completed
        self.turns: list[DialogTurn] = []
        self.is_done: bool = False
        self.max_turns: int = settings.max_conversation_turns
        self.turn_count: int = 0
        self.wrong_person: bool = False

    def initial_greeting(self) -> str:
        greeting = get_greeting(
            parent_name=self.context.parent_name,
            school_name=self.settings.school_name,
            language=self.context.preferred_language,
            gender=self.settings.assistant_gender,
            persona=self.settings.voice_persona,
        )
        self.turns.append(DialogTurn(speaker="agent", text=greeting))
        self.phase = "verify"
        return greeting

    async def handle_parent_utterance(self, utterance: str) -> str:
        """Process incoming speech from the parent and generate next reply."""
        clean_utterance = utterance.strip()
        if not clean_utterance:
            return get_unclear_speech_message(self.context.preferred_language)

        self.turns.append(DialogTurn(speaker="parent", text=clean_utterance))
        self.turn_count += 1

        if self.phase == "verify":
            try:
                confirmed = await self.verifier.is_guardian(
                    clean_utterance, parent_name=self.context.parent_name
                )
            except Exception as e:
                logger.error("Guardian verification failed: %s", e)
                # If verifier errors, fail closed to protect student privacy
                confirmed = False

            if not confirmed:
                self.wrong_person = True
                self.phase = "completed"
                self.is_done = True
                msg = get_wrong_person_message(
                    language=self.context.preferred_language,
                    gender=self.settings.assistant_gender,
                )
                self.turns.append(DialogTurn(speaker="agent", text=msg))
                return msg

            # Confirmed: move to attendance discussion
            self.phase = "discuss"
            date_str = self.context.attendance_date.strftime("%d %B")
            query = get_attendance_query(
                student_name=self.context.student_name,
                date_str=date_str,
                percentage=self.context.attendance_percentage,
                language=self.context.preferred_language,
                gender=self.settings.assistant_gender,
                persona=self.settings.voice_persona,
            )
            self.turns.append(DialogTurn(speaker="agent", text=query))
            return query

        if self.phase == "discuss":
            # If maximum conversational turns reached or parent says closing words
            lower = clean_utterance.casefold()
            closing_intent = any(
                phrase in lower
                for phrase in [
                    "theek hai",
                    "dhanyavaad",
                    "thank you",
                    "bye",
                    "rakh rahe hain",
                    "namaste",
                    "okay",
                ]
            )

            # Check if this should be the final closing response
            if self.turn_count >= self.max_turns or closing_intent:
                closing = get_closing_message(
                    parent_name=self.context.parent_name,
                    language=self.context.preferred_language,
                    gender=self.settings.assistant_gender,
                )
                self.turns.append(DialogTurn(speaker="agent", text=closing))
                self.phase = "completed"
                self.is_done = True
                return closing

            # Generate natural conversational response via LLM
            history = [
                {
                    "role": "assistant" if t.speaker == "agent" else "user",
                    "content": t.text,
                }
                for t in self.turns[-5:]
            ]

            date_str = self.context.attendance_date.strftime("%d %B")
            reply = await self.responder.respond(
                utterance=clean_utterance,
                language=self.context.preferred_language,
                school_name=self.settings.school_name,
                student_name=self.context.student_name,
                attendance_date=date_str,
                attendance_pct=self.context.attendance_percentage,
                threshold=self.context.threshold,
                conversation_history=history,
            )
            self.turns.append(DialogTurn(speaker="agent", text=reply))
            return reply

        # Fallback closing
        self.is_done = True
        closing = get_closing_message(
            parent_name=self.context.parent_name,
            language=self.context.preferred_language,
            gender=self.settings.assistant_gender,
        )
        self.turns.append(DialogTurn(speaker="agent", text=closing))
        return closing

    def get_full_transcript(self) -> str:
        """Format all turns into a readable transcript."""
        lines = []
        for t in self.turns:
            speaker_label = "Agent" if t.speaker == "agent" else "Parent"
            lines.append(f"{speaker_label}: {t.text}")
        return "\n".join(lines)

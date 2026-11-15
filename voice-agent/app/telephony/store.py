import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, create_engine, text


logger = logging.getLogger("attendance_voice.store")


@dataclass(frozen=True)
class CallSession:
    session_id: str
    stream_token: str
    context: dict[str, Any]
    call_sid: str | None
    status: str


class CallStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: Engine | None = None
        self.has_extended_columns: bool = False

    def initialize(self) -> None:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL storage")

        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
        )
        with self.engine.connect() as connection:
            missing_tables = connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM (VALUES
                        ('voice_call_sessions'),
                        ('parent_call_responses')
                    ) AS required(table_name)
                    WHERE to_regclass(table_name) IS NULL
                    """
                )
            ).scalars().all()
            if missing_tables:
                self.dispose()
                raise RuntimeError(
                    "PostgreSQL schema is missing tables; apply "
                    "migrations/001_create_voice_call_tables.sql first"
                )

            # Check if extended columns exist
            existing_cols = set(
                connection.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'parent_call_responses'"
                    )
                ).scalars().all()
            )
            self.has_extended_columns = {
                "response_category",
                "followup_required",
                "callback_at",
                "transcript",
            }.issubset(existing_cols)

    def dispose(self) -> None:
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None

    def expire_stale_sessions(self) -> None:
        with self._engine_required().begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE voice_call_sessions
                    SET status = 'EXPIRED', context_json = NULL,
                        stream_token = NULL
                    WHERE context_json IS NOT NULL
                      AND created_at < now() - INTERVAL '1 hour'
                      AND status NOT IN (
                          'COMPLETED', 'BUSY', 'FAILED', 'NO-ANSWER', 'CANCELED'
                      )
                    """
                )
            )

    def create_session(
        self,
        session_id: str,
        idempotency_key: str,
        stream_token: str,
        context: dict[str, Any],
    ) -> bool:
        with self._engine_required().begin() as connection:
            result = connection.execute(
                text(
                    """
                    INSERT INTO voice_call_sessions
                        (session_id, idempotency_key, stream_token,
                         context_json, status)
                    VALUES (
                        CAST(:session_id AS UUID),
                        :idempotency_key,
                        :stream_token,
                        CAST(:context_json AS JSONB),
                        'CREATING'
                    )
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING session_id
                    """
                ),
                {
                    "session_id": session_id,
                    "idempotency_key": idempotency_key,
                    "stream_token": stream_token,
                    "context_json": json.dumps(context, ensure_ascii=False),
                },
            )
            return result.scalar_one_or_none() is not None

    def find_by_idempotency_key(self, key: str) -> CallSession | None:
        with self._engine_required().connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT session_id, stream_token, context_json, call_sid, status
                    FROM voice_call_sessions
                    WHERE idempotency_key = :idempotency_key
                    """
                ),
                {"idempotency_key": key},
            ).mappings().one_or_none()
        return self._to_session(row)

    def get_session(self, session_id: str) -> CallSession | None:
        with self._engine_required().connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT session_id, stream_token, context_json, call_sid, status
                    FROM voice_call_sessions
                    WHERE session_id = CAST(:session_id AS UUID)
                    """
                ),
                {"session_id": session_id},
            ).mappings().one_or_none()
        return self._to_session(row)

    def bind_call_sid(self, session_id: str, call_sid: str) -> bool:
        with self._engine_required().begin() as connection:
            result = connection.execute(
                text(
                    """
                    UPDATE voice_call_sessions
                    SET call_sid = :call_sid, status = 'RINGING'
                    WHERE session_id = CAST(:session_id AS UUID)
                      AND (call_sid IS NULL OR call_sid = :call_sid)
                    RETURNING session_id
                    """
                ),
                {"session_id": session_id, "call_sid": call_sid},
            )
            return result.scalar_one_or_none() is not None

    def update_status(self, call_sid: str, status: str) -> None:
        normalized_status = status.upper()
        terminal = normalized_status in {
            "COMPLETED",
            "BUSY",
            "FAILED",
            "NO-ANSWER",
            "CANCELED",
        }
        with self._engine_required().begin() as connection:
            if terminal:
                connection.execute(
                    text(
                        """
                        UPDATE voice_call_sessions
                        SET status = :status, context_json = NULL,
                            stream_token = NULL
                        WHERE call_sid = :call_sid
                        """
                    ),
                    {"status": normalized_status, "call_sid": call_sid},
                )
            else:
                connection.execute(
                    text(
                        """
                        UPDATE voice_call_sessions SET status = :status
                        WHERE call_sid = :call_sid
                        """
                    ),
                    {"status": normalized_status, "call_sid": call_sid},
                )

    def update_status_by_session(self, session_id: str, status: str) -> None:
        normalized_status = status.upper()
        terminal = normalized_status in {
            "COMPLETED",
            "BUSY",
            "FAILED",
            "NO-ANSWER",
            "CANCELED",
        }
        with self._engine_required().begin() as connection:
            if terminal:
                connection.execute(
                    text(
                        """
                        UPDATE voice_call_sessions
                        SET status = :status, context_json = NULL,
                            stream_token = NULL
                        WHERE session_id = CAST(:session_id AS UUID)
                        """
                    ),
                    {"status": normalized_status, "session_id": session_id},
                )
            else:
                connection.execute(
                    text(
                        """
                        UPDATE voice_call_sessions SET status = :status
                        WHERE session_id = CAST(:session_id AS UUID)
                        """
                    ),
                    {"status": normalized_status, "session_id": session_id},
                )

    def save_parent_response(
        self,
        session_id: str,
        student_id: str,
        student_name: str,
        response_text: str,
        response_category: str | None = None,
        followup_required: bool = False,
        callback_at: Any | None = None,
        transcript: str | None = None,
    ) -> None:
        with self._engine_required().begin() as connection:
            if self.has_extended_columns:
                connection.execute(
                    text(
                        """
                        INSERT INTO parent_call_responses
                            (session_id, student_id, student_name, response_text,
                             response_category, followup_required, callback_at, transcript)
                        VALUES (
                            CAST(:session_id AS UUID),
                            CAST(:student_id AS UUID),
                            :student_name,
                            :response_text,
                            :response_category,
                            :followup_required,
                            :callback_at,
                            :transcript
                        )
                        ON CONFLICT (session_id) DO UPDATE SET
                            response_text = CASE 
                                WHEN parent_call_responses.response_text = EXCLUDED.response_text THEN EXCLUDED.response_text
                                ELSE parent_call_responses.response_text || E'\\n' || EXCLUDED.response_text
                            END,
                            response_category = COALESCE(EXCLUDED.response_category, parent_call_responses.response_category),
                            followup_required = EXCLUDED.followup_required,
                            callback_at = COALESCE(EXCLUDED.callback_at, parent_call_responses.callback_at),
                            transcript = COALESCE(EXCLUDED.transcript, parent_call_responses.transcript),
                            recorded_at = now()
                        """
                    ),
                    {
                        "session_id": session_id,
                        "student_id": student_id,
                        "student_name": student_name,
                        "response_text": response_text,
                        "response_category": response_category,
                        "followup_required": followup_required,
                        "callback_at": callback_at,
                        "transcript": transcript,
                    },
                )
            else:
                # Fallback to standard schema
                formatted = response_text
                if response_category and not formatted.startswith("["):
                    formatted = f"[{response_category}] {formatted}"
                connection.execute(
                    text(
                        """
                        INSERT INTO parent_call_responses
                            (session_id, student_id, student_name, response_text)
                        VALUES (
                            CAST(:session_id AS UUID),
                            CAST(:student_id AS UUID),
                            :student_name,
                            :response_text
                        )
                        ON CONFLICT (session_id) DO UPDATE SET
                            response_text = CASE 
                                WHEN parent_call_responses.response_text = EXCLUDED.response_text THEN EXCLUDED.response_text
                                ELSE parent_call_responses.response_text || E'\\n' || EXCLUDED.response_text
                            END,
                            recorded_at = now()
                        """
                    ),
                    {
                        "session_id": session_id,
                        "student_id": student_id,
                        "student_name": student_name,
                        "response_text": formatted,
                    },
                )

    def _engine_required(self) -> Engine:
        if self.engine is None:
            raise RuntimeError("PostgreSQL store has not been initialized")
        return self.engine

    @staticmethod
    def _to_session(row: Mapping[str, Any] | None) -> CallSession | None:
        if row is None:
            return None

        stream_token = row["stream_token"]
        context = row["context_json"]
        if stream_token is None or context is None:
            return None
        if isinstance(context, str):
            context = json.loads(context)

        session_id = row["session_id"]
        if isinstance(session_id, UUID):
            session_id = str(session_id)
        return CallSession(
            session_id=session_id,
            stream_token=stream_token,
            context=context,
            call_sid=row["call_sid"],
            status=row["status"],
        )

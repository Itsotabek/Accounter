from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from fifo_accounting_bot.database import SessionFactory
from fifo_accounting_bot.models import TelegramUser


@dataclass(frozen=True, slots=True)
class UserPreferences:
    telegram_user_id: int
    username: str | None
    display_name: str
    language: str | None
    ai_enabled: bool
    is_blocked: bool
    first_seen_at: datetime
    last_seen_at: datetime


class UserService:
    def __init__(self, session_factory: SessionFactory):
        self._sessions = session_factory

    def touch(
        self, telegram_user_id: int, username: str | None, display_name: str
    ) -> UserPreferences:
        with self._sessions.begin() as session:
            row = session.get(TelegramUser, telegram_user_id)
            if row is None:
                row = TelegramUser(
                    telegram_user_id=telegram_user_id,
                    username=username,
                    display_name=display_name,
                )
                session.add(row)
            else:
                row.username = username
                row.display_name = display_name
                row.last_seen_at = datetime.now(timezone.utc)
            session.flush()
            return self._result(row)

    def get(self, telegram_user_id: int) -> UserPreferences | None:
        with self._sessions() as session:
            row = session.get(TelegramUser, telegram_user_id)
            return self._result(row) if row else None

    def set_language(self, telegram_user_id: int, language: str) -> None:
        with self._sessions.begin() as session:
            row = session.get(TelegramUser, telegram_user_id)
            if row is None:
                row = TelegramUser(
                    telegram_user_id=telegram_user_id,
                    language=language,
                )
                session.add(row)
            else:
                row.language = language

    def set_ai_enabled(self, telegram_user_id: int, enabled: bool) -> None:
        with self._sessions.begin() as session:
            row = session.get(TelegramUser, telegram_user_id)
            if row is None:
                row = TelegramUser(
                    telegram_user_id=telegram_user_id,
                    ai_enabled=enabled,
                )
                session.add(row)
            else:
                row.ai_enabled = enabled

    def list_users(self, limit: int = 50) -> list[UserPreferences]:
        with self._sessions() as session:
            rows = list(
                session.scalars(
                    select(TelegramUser)
                    .order_by(TelegramUser.last_seen_at.desc())
                    .limit(max(1, min(limit, 200)))
                )
            )
        return [self._result(row) for row in rows]

    @staticmethod
    def _result(row: TelegramUser) -> UserPreferences:
        return UserPreferences(
            telegram_user_id=row.telegram_user_id,
            username=row.username,
            display_name=row.display_name,
            language=row.language,
            ai_enabled=row.ai_enabled,
            is_blocked=row.is_blocked,
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
        )

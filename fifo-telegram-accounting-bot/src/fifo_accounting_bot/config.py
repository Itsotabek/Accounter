from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    database_url: str = "sqlite:///./fifo_bot.db"
    log_level: str = "INFO"
    allowed_telegram_user_ids: frozenset[int] = frozenset()
    owner_telegram_user_ids: frozenset[int] = frozenset()
    bot_owner_name: str = "Administrator of @fifo_accounter_bot"
    support_contact: str = "@fifo_accounter_bot"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.6-luna"
    ai_max_output_tokens: int = 450

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is missing. Copy .env.example to .env and add your BotFather token."
            )

        raw_allowed_ids = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").strip()
        raw_owner_ids = os.getenv("OWNER_TELEGRAM_USER_IDS", "").strip()
        try:
            allowed_ids = frozenset(
                int(value.strip())
                for value in raw_allowed_ids.split(",")
                if value.strip()
            )
            owner_ids = frozenset(
                int(value.strip())
                for value in raw_owner_ids.split(",")
                if value.strip()
            )
        except ValueError as exc:
            raise RuntimeError(
                "ALLOWED_TELEGRAM_USER_IDS and OWNER_TELEGRAM_USER_IDS must be comma-separated integers."
            ) from exc

        try:
            ai_max_output_tokens = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "450"))
        except ValueError as exc:
            raise RuntimeError("AI_MAX_OUTPUT_TOKENS must be an integer.") from exc
        if not 100 <= ai_max_output_tokens <= 1200:
            raise RuntimeError("AI_MAX_OUTPUT_TOKENS must be between 100 and 1200.")

        return cls(
            telegram_bot_token=token,
            database_url=os.getenv("DATABASE_URL", "sqlite:///./fifo_bot.db").strip(),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
            allowed_telegram_user_ids=allowed_ids,
            owner_telegram_user_ids=owner_ids,
            bot_owner_name=os.getenv(
                "BOT_OWNER_NAME", "Administrator of @fifo_accounter_bot"
            ).strip(),
            support_contact=os.getenv("SUPPORT_CONTACT", "@fifo_accounter_bot").strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip(),
            ai_max_output_tokens=ai_max_output_tokens,
        )

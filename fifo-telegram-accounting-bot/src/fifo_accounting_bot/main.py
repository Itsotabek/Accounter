from __future__ import annotations

import logging
import os

from fifo_accounting_bot.bot.app import create_application
from fifo_accounting_bot.config import Settings
from fifo_accounting_bot.database import (
    create_database_engine,
    create_schema,
    create_session_factory,
)
from fifo_accounting_bot.legacy_migration import migrate_legacy_payload
from fifo_accounting_bot.services import InventoryService


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        level=getattr(logging, settings.log_level, logging.INFO),
    )
    # httpx includes the full Telegram API URL at INFO level. That URL contains
    # the bot token, so keep transport logs at WARNING even when app logs are INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    engine = create_database_engine(settings.database_url)
    create_schema(engine)
    migration_payload = os.getenv("LEGACY_SQLITE_MIGRATION_PAYLOAD", "").strip()
    if migration_payload:
        migration = migrate_legacy_payload(engine, migration_payload)
        logging.getLogger(__name__).info(
            "Legacy migration status=%s source=%s before=%s after=%s reason=%s",
            migration.status,
            migration.source_counts,
            migration.before_counts,
            migration.after_counts,
            migration.reason,
        )
    service = InventoryService(create_session_factory(engine))
    application = create_application(settings, service)
    logging.getLogger(__name__).info("Starting Accounter Telegram bot")
    application.run_polling()


if __name__ == "__main__":
    main()

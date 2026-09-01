from __future__ import annotations

import pytest

from fifo_accounting_bot.database import (
    create_database_engine,
    create_schema,
    create_session_factory,
)
from fifo_accounting_bot.services import InventoryService


@pytest.fixture
def inventory(tmp_path):
    database_path = tmp_path / "test_inventory.db"
    engine = create_database_engine(f"sqlite:///{database_path.as_posix()}")
    create_schema(engine)
    session_factory = create_session_factory(engine)
    try:
        yield InventoryService(session_factory), session_factory
    finally:
        engine.dispose()

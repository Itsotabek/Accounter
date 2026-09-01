from __future__ import annotations

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from fifo_accounting_bot.models import Base

SessionFactory = sessionmaker[Session]


def normalize_database_url(database_url: str) -> str:
    """Select psycopg 3 when a provider supplies a generic PostgreSQL URL."""
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


def create_database_engine(database_url: str) -> Engine:
    database_url = normalize_database_url(database_url)
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}

    engine = create_engine(database_url, **engine_options)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: Engine) -> SessionFactory:
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)

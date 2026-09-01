from fifo_accounting_bot.database import normalize_database_url


def test_railway_postgresql_url_uses_psycopg_3() -> None:
    url = "postgresql://user:password@postgres.railway.internal:5432/app"

    assert normalize_database_url(url) == (
        "postgresql+psycopg://user:password@postgres.railway.internal:5432/app"
    )


def test_legacy_postgres_url_uses_psycopg_3() -> None:
    url = "postgres://user:password@host:5432/app"

    assert normalize_database_url(url).startswith("postgresql+psycopg://")


def test_explicit_driver_and_sqlite_urls_are_unchanged() -> None:
    explicit = "postgresql+psycopg://user:password@host:5432/app"
    sqlite = "sqlite:///./fifo_bot.db"

    assert normalize_database_url(explicit) == explicit
    assert normalize_database_url(sqlite) == sqlite

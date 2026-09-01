from __future__ import annotations

import base64
import hashlib
import json
import logging
import zlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine, text


LOGGER = logging.getLogger(__name__)

PAYLOAD_FORMAT = "accounter-sqlite-v1"

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "telegram_users": (
        "telegram_user_id", "username", "display_name", "language",
        "ai_enabled", "is_blocked", "first_seen_at", "last_seen_at",
    ),
    "products": ("id", "owner_id", "sku", "name", "unit", "created_at"),
    "purchase_batches": (
        "id", "product_id", "purchased_on", "original_quantity",
        "remaining_quantity", "unit_cost", "created_at",
    ),
    "sales": (
        "id", "product_id", "sold_on", "quantity", "revenue", "cogs", "created_at",
    ),
    "sale_allocations": (
        "id", "sale_id", "purchase_batch_id", "quantity", "unit_cost", "cost",
    ),
    "journal_entries": (
        "id", "owner_id", "entry_date", "reference_type", "reference_id",
        "debit_account", "credit_account", "amount", "memo", "created_at",
    ),
    "archived_products": ("id", "product_id", "owner_id", "archived_at"),
    "accounts": (
        "id", "owner_id", "code", "name", "account_type", "subtype",
        "is_active", "created_at",
    ),
    "contacts": (
        "id", "owner_id", "contact_type", "display_name", "email", "phone",
        "tax_id", "notes", "is_active", "created_at",
    ),
    "ledger_transactions": (
        "id", "owner_id", "transaction_date", "kind", "description", "reference",
        "source_key", "contact_id", "status", "reversal_of_id", "created_at",
    ),
    "ledger_lines": (
        "id", "transaction_id", "account_id", "debit", "credit", "memo",
    ),
    "accounting_documents": (
        "id", "owner_id", "document_type", "number", "contact_id", "issue_date",
        "due_date", "description", "subtotal", "tax_amount", "total", "paid_amount",
        "status", "transaction_id", "created_at",
    ),
    "payments": (
        "id", "owner_id", "document_id", "paid_on", "amount", "direction",
        "account_code", "reference", "transaction_id", "created_at",
    ),
}

BUSINESS_TABLES = tuple(
    table for table in TABLE_COLUMNS if table not in {"telegram_users", "accounts"}
)

DATE_COLUMNS = {
    "purchased_on", "sold_on", "entry_date", "transaction_date",
    "issue_date", "due_date", "paid_on",
}
DATETIME_COLUMNS = {"created_at", "first_seen_at", "last_seen_at", "archived_at"}
DECIMAL_COLUMNS = {
    "original_quantity", "remaining_quantity", "unit_cost", "quantity", "revenue",
    "cogs", "cost", "amount", "debit", "credit", "subtotal", "tax_amount",
    "total", "paid_amount",
}
BOOLEAN_COLUMNS = {"ai_enabled", "is_blocked", "is_active"}


@dataclass(frozen=True, slots=True)
class MigrationResult:
    status: str
    source_counts: dict[str, int]
    before_counts: dict[str, int]
    after_counts: dict[str, int]
    reason: str = ""


def decode_payload(encoded: str) -> tuple[dict[str, list[dict[str, Any]]], str]:
    try:
        compressed = base64.urlsafe_b64decode(encoded.encode("ascii"))
        raw = zlib.decompress(compressed)
        document = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Legacy migration payload is invalid.") from exc

    if document.get("format") != PAYLOAD_FORMAT:
        raise ValueError("Legacy migration payload format is unsupported.")
    tables = document.get("tables")
    if not isinstance(tables, dict):
        raise ValueError("Legacy migration payload has no table data.")

    validated: dict[str, list[dict[str, Any]]] = {}
    for table, columns in TABLE_COLUMNS.items():
        rows = tables.get(table, [])
        if not isinstance(rows, list):
            raise ValueError(f"Legacy migration table {table} is invalid.")
        clean_rows: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(columns):
                raise ValueError(f"Legacy migration row for {table} has an invalid schema.")
            clean_rows.append(_normalize_row(row))
        validated[table] = clean_rows

    return validated, hashlib.sha256(raw).hexdigest()


def migrate_legacy_payload(engine: Engine, encoded: str) -> MigrationResult:
    tables, digest = decode_payload(encoded)
    source_counts = {table: len(rows) for table, rows in tables.items()}

    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS legacy_migrations ("
            "digest VARCHAR(64) PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), "
            "source_counts TEXT NOT NULL)"
        ))
        before = _target_counts(connection)
        already_applied = connection.execute(
            text("SELECT 1 FROM legacy_migrations WHERE digest = :digest"),
            {"digest": digest},
        ).scalar_one_or_none()
        if already_applied:
            return MigrationResult("already_applied", source_counts, before, before)

        occupied = {table: before[table] for table in BUSINESS_TABLES if before[table]}
        if occupied:
            reason = "Railway already contains business records: " + ", ".join(
                f"{table}={count}" for table, count in occupied.items()
            )
            LOGGER.warning("Legacy migration skipped safely. %s", reason)
            return MigrationResult("blocked", source_counts, before, before, reason)

        _merge_users(connection, tables["telegram_users"])
        account_map = _merge_accounts(connection, tables["accounts"])

        for table in ("products", "contacts", "purchase_batches", "sales", "sale_allocations", "journal_entries", "archived_products"):
            _insert_rows(connection, table, tables[table])

        _insert_ledger_transactions(connection, tables["ledger_transactions"])
        _insert_ledger_lines(connection, tables["ledger_lines"], account_map)
        _insert_rows(connection, "accounting_documents", tables["accounting_documents"])
        _insert_rows(connection, "payments", tables["payments"])

        for table in TABLE_COLUMNS:
            if table not in {"telegram_users", "accounts"} and "id" in TABLE_COLUMNS[table]:
                _reset_sequence(connection, table)

        connection.execute(
            text("INSERT INTO legacy_migrations (digest, source_counts) VALUES (:digest, :counts)"),
            {"digest": digest, "counts": json.dumps(source_counts, sort_keys=True)},
        )
        after = _target_counts(connection)

    return MigrationResult("applied", source_counts, before, after)


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for column, value in normalized.items():
        if value is None:
            continue
        if column in DATE_COLUMNS:
            normalized[column] = date.fromisoformat(str(value))
        elif column in DATETIME_COLUMNS:
            normalized[column] = datetime.fromisoformat(str(value))
        elif column in DECIMAL_COLUMNS:
            normalized[column] = Decimal(str(value))
        elif column in BOOLEAN_COLUMNS:
            normalized[column] = bool(value)
    return normalized


def _target_counts(connection: Any) -> dict[str, int]:
    return {
        table: int(connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
        for table in TABLE_COLUMNS
    }


def _merge_users(connection: Any, rows: list[dict[str, Any]]) -> None:
    statement = text(
        "INSERT INTO telegram_users (telegram_user_id, username, display_name, language, "
        "ai_enabled, is_blocked, first_seen_at, last_seen_at) VALUES ("
        ":telegram_user_id, :username, :display_name, :language, :ai_enabled, :is_blocked, "
        ":first_seen_at, :last_seen_at) ON CONFLICT (telegram_user_id) DO UPDATE SET "
        "username = COALESCE(EXCLUDED.username, telegram_users.username), "
        "display_name = CASE WHEN EXCLUDED.display_name <> '' THEN EXCLUDED.display_name ELSE telegram_users.display_name END, "
        "language = COALESCE(telegram_users.language, EXCLUDED.language), "
        "ai_enabled = telegram_users.ai_enabled OR EXCLUDED.ai_enabled, "
        "is_blocked = telegram_users.is_blocked OR EXCLUDED.is_blocked, "
        "first_seen_at = LEAST(telegram_users.first_seen_at, EXCLUDED.first_seen_at), "
        "last_seen_at = GREATEST(telegram_users.last_seen_at, EXCLUDED.last_seen_at)"
    )
    for row in rows:
        connection.execute(statement, row)


def _merge_accounts(connection: Any, rows: list[dict[str, Any]]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    select_existing = text(
        "SELECT id FROM accounts WHERE owner_id = :owner_id AND (code = :code OR name = :name) "
        "ORDER BY CASE WHEN code = :code THEN 0 ELSE 1 END LIMIT 1"
    )
    insert_account = text(
        "INSERT INTO accounts (owner_id, code, name, account_type, subtype, is_active, created_at) "
        "VALUES (:owner_id, :code, :name, :account_type, :subtype, :is_active, :created_at) RETURNING id"
    )
    for row in rows:
        target_id = connection.execute(select_existing, row).scalar_one_or_none()
        if target_id is None:
            target_id = connection.execute(insert_account, row).scalar_one()
        mapping[int(row["id"])] = int(target_id)
    return mapping


def _insert_rows(connection: Any, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = TABLE_COLUMNS[table]
    statement = text(
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join(':' + column for column in columns)})"
    )
    for row in rows:
        connection.execute(statement, row)


def _insert_ledger_transactions(connection: Any, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    staged = [dict(row, reversal_of_id=None) for row in rows]
    _insert_rows(connection, "ledger_transactions", staged)
    update = text("UPDATE ledger_transactions SET reversal_of_id = :reversal WHERE id = :id")
    for row in rows:
        if row["reversal_of_id"] is not None:
            connection.execute(update, {"id": row["id"], "reversal": row["reversal_of_id"]})


def _insert_ledger_lines(
    connection: Any,
    rows: list[dict[str, Any]],
    account_map: dict[int, int],
) -> None:
    remapped: list[dict[str, Any]] = []
    for row in rows:
        mapped = dict(row)
        mapped["account_id"] = account_map[int(row["account_id"])]
        remapped.append(mapped)
    _insert_rows(connection, "ledger_lines", remapped)


def _reset_sequence(connection: Any, table: str) -> None:
    connection.execute(text(
        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
        f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
        f"EXISTS(SELECT 1 FROM {table}))"
    ))


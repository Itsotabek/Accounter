import base64
import json
import zlib

import pytest

from fifo_accounting_bot.legacy_migration import PAYLOAD_FORMAT, TABLE_COLUMNS, decode_payload


def _payload() -> str:
    document = {
        "format": PAYLOAD_FORMAT,
        "tables": {table: [] for table in TABLE_COLUMNS},
    }
    raw = json.dumps(document).encode("utf-8")
    return base64.urlsafe_b64encode(zlib.compress(raw)).decode("ascii")


def test_decode_empty_payload() -> None:
    tables, digest = decode_payload(_payload())

    assert set(tables) == set(TABLE_COLUMNS)
    assert all(not rows for rows in tables.values())
    assert len(digest) == 64


def test_decode_rejects_unknown_format() -> None:
    document = {"format": "other", "tables": {}}
    raw = json.dumps(document).encode("utf-8")
    encoded = base64.urlsafe_b64encode(zlib.compress(raw)).decode("ascii")

    with pytest.raises(ValueError, match="unsupported"):
        decode_payload(encoded)


def test_decode_rejects_wrong_row_schema() -> None:
    document = {
        "format": PAYLOAD_FORMAT,
        "tables": {table: [] for table in TABLE_COLUMNS},
    }
    document["tables"]["telegram_users"] = [{"telegram_user_id": 1}]
    raw = json.dumps(document).encode("utf-8")
    encoded = base64.urlsafe_b64encode(zlib.compress(raw)).decode("ascii")

    with pytest.raises(ValueError, match="invalid schema"):
        decode_payload(encoded)

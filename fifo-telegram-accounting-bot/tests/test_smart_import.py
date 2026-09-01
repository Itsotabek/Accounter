from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import cv2

from fifo_accounting_bot.bot.smart_import import decode_qr_image, parse_smart_payload
from fifo_accounting_bot.exceptions import ValidationError


def test_plain_sku_and_product_uri_create_lookup_payloads():
    assert parse_smart_payload("coffee-1").sku == "COFFEE-1"
    payload = parse_smart_payload("fifo://product/coffee-1")
    assert payload.kind == "lookup"
    assert payload.sku == "COFFEE-1"


def test_purchase_json_prefills_transaction():
    payload = parse_smart_payload(
        '{"type":"purchase","sku":"beans","quantity":10,"unit_cost":8.5,"date":"2026-08-31"}'
    )
    assert payload.kind == "purchase"
    assert payload.sku == "BEANS"
    assert payload.quantity == Decimal("10")
    assert payload.unit_cost == Decimal("8.5")
    assert payload.occurred_on == date(2026, 8, 31)


def test_sale_fifo_uri_prefills_transaction():
    payload = parse_smart_payload(
        "fifo://sale/BEANS?quantity=2&unit_price=14&date=2026-08-31"
    )
    assert payload.kind == "sale"
    assert payload.quantity == Decimal("2")
    assert payload.unit_price == Decimal("14")


def test_invalid_or_unsafe_payload_is_rejected():
    with pytest.raises(ValidationError):
        parse_smart_payload('{"type":"sale","sku":"ABC","quantity":-1}')
    with pytest.raises(ValidationError):
        parse_smart_payload("not a supported free-form sentence")


def test_real_qr_image_round_trip():
    raw = "fifo://purchase/BEANS?quantity=10&unit_cost=8.5&date=2026-08-31"
    image = cv2.QRCodeEncoder_create().encode(raw)
    image = cv2.copyMakeBorder(
        image, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255
    )
    image = cv2.resize(image, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
    encoded_ok, encoded = cv2.imencode(".png", image)

    assert encoded_ok
    decoded = decode_qr_image(encoded.tobytes())
    payload = parse_smart_payload(decoded)
    assert payload.kind == "purchase"
    assert payload.quantity == Decimal("10")

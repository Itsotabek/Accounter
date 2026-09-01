from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal
from urllib.parse import parse_qs, unquote, urlparse

from fifo_accounting_bot.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class SmartPayload:
    kind: Literal["lookup", "product", "purchase", "sale"]
    sku: str
    name: str | None = None
    unit: str | None = None
    quantity: Decimal | None = None
    unit_cost: Decimal | None = None
    unit_price: Decimal | None = None
    occurred_on: date | None = None


def decode_qr_image(image_bytes: bytes) -> str:
    """Decode the first QR value from Telegram image bytes."""
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ValidationError(
            "QR scanning support is not installed. Install the project dependencies again."
        ) from exc

    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValidationError("That image could not be read.")

    detector = cv2.QRCodeDetector()
    value, points, _ = detector.detectAndDecode(image)
    if value and points is not None:
        return value.strip()

    try:
        found, values, _, _ = detector.detectAndDecodeMulti(image)
    except (AttributeError, cv2.error):
        found, values = False, ()
    if found:
        for candidate in values:
            if candidate.strip():
                return candidate.strip()
    raise ValidationError(
        "No readable QR code was found. Move closer, improve lighting, and try again."
    )


def parse_smart_payload(raw: str) -> SmartPayload:
    value = raw.strip()
    if not value:
        raise ValidationError("The QR or pasted data is empty.")

    if value.startswith("{"):
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValidationError("The JSON payload is not valid.") from exc
        if not isinstance(data, dict):
            raise ValidationError("The JSON payload must be an object.")
        return _from_mapping(data)

    if value.lower().startswith("fifo://"):
        parsed = urlparse(value)
        kind = parsed.netloc.lower()
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        path_sku = unquote(parsed.path.strip("/"))
        if path_sku and "sku" not in query:
            query["sku"] = path_sku
        if kind == "product" and "name" not in query and "unit" not in query:
            if not query.get("sku"):
                raise ValidationError("The product QR is missing an SKU.")
            return SmartPayload(kind="lookup", sku=str(query["sku"]).strip().upper())
        query["type"] = kind
        return _from_mapping(query)

    if len(value) <= 64 and not any(character.isspace() for character in value):
        return SmartPayload(kind="lookup", sku=value.upper())

    raise ValidationError(
        "Use a plain SKU, a fifo:// QR value, or a supported JSON object."
    )


def _from_mapping(data: dict[str, object]) -> SmartPayload:
    kind = str(data.get("type", "")).strip().lower()
    if kind not in {"product", "purchase", "sale"}:
        raise ValidationError("Payload type must be product, purchase, or sale.")
    sku = _required_text(data, "sku", 64).upper()
    occurred_on = _optional_date(data.get("date"))

    if kind == "product":
        return SmartPayload(
            kind="product",
            sku=sku,
            name=_required_text(data, "name", 200),
            unit=_required_text(data, "unit", 32).lower(),
        )
    if kind == "purchase":
        return SmartPayload(
            kind="purchase",
            sku=sku,
            quantity=_required_decimal(data, "quantity", allow_zero=False),
            unit_cost=_required_decimal(data, "unit_cost", allow_zero=True),
            occurred_on=occurred_on,
        )
    return SmartPayload(
        kind="sale",
        sku=sku,
        quantity=_required_decimal(data, "quantity", allow_zero=False),
        unit_price=_optional_decimal(data.get("unit_price"), "unit_price"),
        occurred_on=occurred_on,
    )


def _required_text(data: dict[str, object], field: str, maximum: int) -> str:
    value = str(data.get(field, "")).strip()
    if not value or len(value) > maximum:
        raise ValidationError(f"{field} must contain 1 to {maximum} characters.")
    return value


def _required_decimal(
    data: dict[str, object], field: str, *, allow_zero: bool
) -> Decimal:
    if field not in data:
        raise ValidationError(f"The payload is missing {field}.")
    return _decimal(data[field], field, allow_zero=allow_zero)


def _optional_decimal(value: object, field: str) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    return _decimal(value, field, allow_zero=True)


def _decimal(value: object, field: str, *, allow_zero: bool) -> Decimal:
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValidationError(f"{field} must be a valid number.") from exc
    if not result.is_finite() or result < 0 or (result == 0 and not allow_zero):
        comparison = "zero or greater" if allow_zero else "greater than zero"
        raise ValidationError(f"{field} must be {comparison}.")
    return result


def _optional_date(value: object) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ValidationError("date must use YYYY-MM-DD.") from exc

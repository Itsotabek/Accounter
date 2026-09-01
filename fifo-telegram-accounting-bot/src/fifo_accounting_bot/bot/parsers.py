from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from fifo_accounting_bot.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class AddProductCommand:
    sku: str
    name: str
    unit: str


@dataclass(frozen=True, slots=True)
class PurchaseCommand:
    sku: str
    quantity: Decimal
    unit_cost: Decimal
    purchased_on: date | None


@dataclass(frozen=True, slots=True)
class SaleCommand:
    sku: str
    quantity: Decimal
    unit_sale_price: Decimal | None
    sold_on: date | None


def command_payload(message_text: str | None) -> str:
    if not message_text:
        return ""
    parts = message_text.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else ""


def parse_add_product(payload: str) -> AddProductCommand:
    parts = [part.strip() for part in payload.split("|")]
    if len(parts) != 3 or not all(parts):
        raise ValidationError("Usage: /addproduct SKU | Product name | unit")
    return AddProductCommand(sku=parts[0], name=parts[1], unit=parts[2])


def parse_purchase(payload: str) -> PurchaseCommand:
    parts = payload.split()
    if len(parts) not in (3, 4):
        raise ValidationError("Usage: /purchase SKU QUANTITY UNIT_COST [YYYY-MM-DD]")
    return PurchaseCommand(
        sku=parts[0],
        quantity=_parse_decimal(parts[1], "quantity"),
        unit_cost=_parse_decimal(parts[2], "unit cost"),
        purchased_on=_parse_date(parts[3]) if len(parts) == 4 else None,
    )


def parse_sale(payload: str) -> SaleCommand:
    parts = payload.split()
    if len(parts) < 2 or len(parts) > 4:
        raise ValidationError("Usage: /sale SKU QUANTITY [UNIT_PRICE] [YYYY-MM-DD]")

    price: Decimal | None = None
    sold_on: date | None = None
    if len(parts) == 3:
        if _looks_like_iso_date(parts[2]):
            sold_on = _parse_date(parts[2])
        else:
            price = _parse_decimal(parts[2], "unit sale price")
    elif len(parts) == 4:
        price = _parse_decimal(parts[2], "unit sale price")
        sold_on = _parse_date(parts[3])

    return SaleCommand(
        sku=parts[0],
        quantity=_parse_decimal(parts[1], "quantity"),
        unit_sale_price=price,
        sold_on=sold_on,
    )


def parse_stock(payload: str) -> str | None:
    parts = payload.split()
    if len(parts) > 1:
        raise ValidationError("Usage: /stock [SKU]")
    return parts[0] if parts else None


def parse_report(payload: str) -> tuple[date | None, date | None]:
    parts = payload.split()
    if not parts:
        return None, None
    if len(parts) != 2:
        raise ValidationError("Usage: /report [START_DATE END_DATE]")
    return _parse_date(parts[0]), _parse_date(parts[1])


def _parse_decimal(raw: str, field: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValidationError(f"Invalid {field}: {raw!r}.") from exc
    if not value.is_finite():
        raise ValidationError(f"Invalid {field}: value must be finite.")
    return value


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(f"Invalid date {raw!r}; use YYYY-MM-DD.") from exc


def _looks_like_iso_date(raw: str) -> bool:
    return len(raw) == 10 and raw[4:5] == "-" and raw[7:8] == "-"

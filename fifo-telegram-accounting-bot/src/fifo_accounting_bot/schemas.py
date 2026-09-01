from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ProductResult:
    id: int
    sku: str
    name: str
    unit: str


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    batch_id: int
    sku: str
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    purchased_on: date


@dataclass(frozen=True, slots=True)
class FifoLayer:
    batch_id: int
    purchased_on: date
    quantity: Decimal
    unit_cost: Decimal
    cost: Decimal


@dataclass(frozen=True, slots=True)
class SaleResult:
    sale_id: int
    sku: str
    quantity: Decimal
    sold_on: date
    revenue: Decimal | None
    cogs: Decimal
    gross_profit: Decimal | None
    layers: tuple[FifoLayer, ...]


@dataclass(frozen=True, slots=True)
class StockLine:
    sku: str
    name: str
    unit: str
    quantity: Decimal
    inventory_value: Decimal


@dataclass(frozen=True, slots=True)
class InventoryReport:
    period_start: date | None
    period_end: date | None
    sales_count: int
    unpriced_sales_count: int
    units_sold: Decimal
    revenue: Decimal
    cogs: Decimal
    priced_cogs: Decimal
    gross_profit: Decimal
    inventory_units: Decimal
    inventory_value: Decimal


@dataclass(frozen=True, slots=True)
class ActivityLine:
    kind: str
    reference_id: int
    occurred_on: date
    created_at: datetime
    sku: str
    quantity: Decimal
    amount: Decimal | None
    cogs: Decimal | None

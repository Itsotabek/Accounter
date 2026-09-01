from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from fifo_accounting_bot.exceptions import InsufficientStockError, NotFoundError, ValidationError
from fifo_accounting_bot.models import JournalEntry, ProductTranslation, PurchaseBatch, Sale, SaleAllocation


def test_sale_consumes_oldest_dated_batches_first(inventory):
    service, sessions = inventory
    owner_id = 101
    service.add_product(owner_id, "BEANS", "Coffee beans", "kg")

    newer = service.record_purchase(
        owner_id, "BEANS", "10", "5.00", date(2026, 1, 10)
    )
    older = service.record_purchase(
        owner_id, "BEANS", "10", "4.00", date(2026, 1, 1)
    )

    sale = service.record_sale(
        owner_id, "BEANS", "15", "10.00", date(2026, 1, 20)
    )

    assert sale.cogs == Decimal("65.0000")
    assert sale.revenue == Decimal("150.0000")
    assert sale.gross_profit == Decimal("85.0000")
    assert [layer.batch_id for layer in sale.layers] == [older.batch_id, newer.batch_id]
    assert [layer.quantity for layer in sale.layers] == [
        Decimal("10.0000"),
        Decimal("5.0000"),
    ]

    stock = service.get_stock(owner_id, "BEANS")
    assert stock[0].quantity == Decimal("5.0000")
    assert stock[0].inventory_value == Decimal("25.0000")

    with sessions() as session:
        allocations = session.scalars(
            select(SaleAllocation)
            .where(SaleAllocation.sale_id == sale.sale_id)
            .order_by(SaleAllocation.id)
        ).all()
        assert len(allocations) == 2
        assert session.scalar(select(func.count(JournalEntry.id))) == 4


def test_insufficient_stock_rolls_back_entire_sale(inventory):
    service, sessions = inventory
    owner_id = 202
    service.add_product(owner_id, "PAPER", "Printer paper", "ream")
    service.record_purchase(owner_id, "PAPER", "3", "6.25", date(2026, 2, 1))

    with pytest.raises(InsufficientStockError, match="requested 4.0000, available 3.0000"):
        service.record_sale(owner_id, "PAPER", "4", "9.00", date(2026, 2, 2))

    assert service.get_stock(owner_id, "PAPER")[0].quantity == Decimal("3.0000")
    with sessions() as session:
        assert session.scalar(select(func.count(Sale.id))) == 0
        assert session.scalar(select(func.count(SaleAllocation.id))) == 0
        assert session.scalar(select(func.count(JournalEntry.id))) == 1


def test_report_uses_recorded_revenue_and_fifo_cogs(inventory):
    service, _ = inventory
    owner_id = 303
    service.add_product(owner_id, "WIDGET", "Widget", "pcs")
    service.record_purchase(owner_id, "WIDGET", "10", "2.00", date(2026, 3, 1))
    service.record_sale(owner_id, "WIDGET", "4", "5.00", date(2026, 3, 2))
    service.record_sale(owner_id, "WIDGET", "1", None, date(2026, 3, 3))

    report = service.get_report(owner_id, date(2026, 3, 1), date(2026, 3, 31))

    assert report.sales_count == 2
    assert report.unpriced_sales_count == 1
    assert report.units_sold == Decimal("5.0000")
    assert report.revenue == Decimal("20.0000")
    assert report.cogs == Decimal("10.0000")
    assert report.priced_cogs == Decimal("8.0000")
    assert report.gross_profit == Decimal("12.0000")
    assert report.inventory_units == Decimal("5.0000")
    assert report.inventory_value == Decimal("10.0000")


def test_inventory_is_isolated_by_telegram_user(inventory):
    service, _ = inventory
    service.add_product(1, "SAME-SKU", "Owner one's item", "pcs")
    service.add_product(2, "SAME-SKU", "Owner two's item", "pcs")
    service.record_purchase(1, "SAME-SKU", "7", "1.00")
    service.record_purchase(2, "SAME-SKU", "2", "3.00")

    assert service.get_stock(1, "SAME-SKU")[0].quantity == Decimal("7.0000")
    assert service.get_stock(2, "SAME-SKU")[0].quantity == Decimal("2.0000")


def test_product_name_and_unit_follow_selected_language(inventory):
    service, sessions = inventory
    owner_id = 313
    service.add_product(owner_id, "PENCIL", "Pencil", "pieces", language="en")

    assert service.get_stock(owner_id, "PENCIL", "en")[0].name == "Pencil"
    uzbek = service.get_stock(owner_id, "PENCIL", "uz")[0]
    assert uzbek.name == "Qalam"
    assert uzbek.unit == "dona"

    with sessions() as session:
        assert session.scalar(select(func.count(ProductTranslation.id))) == 5


def test_existing_standard_product_without_translation_rows_uses_glossary(inventory):
    service, _ = inventory
    owner_id = 314
    service.add_product(owner_id, "PENCIL", "Pencil", "pcs")

    assert service.get_stock(owner_id, "PENCIL", "uz")[0].name == "Qalam"


def test_unknown_brand_name_is_preserved_across_languages(inventory):
    service, _ = inventory
    owner_id = 315
    service.add_product(owner_id, "BRAND", "Acme Ultra", "pcs", language="en")

    assert service.get_stock(owner_id, "BRAND", "it")[0].name == "Acme Ultra"


def test_same_day_batches_use_creation_order(inventory):
    service, _ = inventory
    owner_id = 404
    service.add_product(owner_id, "OIL", "Cooking oil", "l")
    first = service.record_purchase(owner_id, "OIL", "2", "3.00", date(2026, 4, 1))
    second = service.record_purchase(owner_id, "OIL", "2", "4.00", date(2026, 4, 1))

    sale = service.record_sale(owner_id, "OIL", "3", sold_on=date(2026, 4, 2))

    assert [layer.batch_id for layer in sale.layers] == [first.batch_id, second.batch_id]
    assert sale.cogs == Decimal("10.0000")


def test_smart_suggestions_and_recent_activity(inventory):
    service, _ = inventory
    owner_id = 505
    service.add_product(owner_id, "SMART", "Smart item", "pcs")
    service.record_purchase(owner_id, "SMART", "10", "3.50", date(2026, 5, 1))
    service.record_sale(owner_id, "SMART", "2", "8.00", date(2026, 5, 2))

    assert service.get_last_purchase_unit_cost(owner_id, "SMART") == Decimal("3.5000")
    assert service.get_last_sale_unit_price(owner_id, "SMART") == Decimal("8.0000")

    activity = service.get_recent_activity(owner_id)
    assert [item.kind for item in activity] == ["sale", "purchase"]
    assert activity[0].sku == "SMART"
    assert activity[0].cogs == Decimal("7.0000")


def test_remove_product_requires_zero_stock_and_preserves_history(inventory):
    service, sessions = inventory
    owner_id = 606
    service.add_product(owner_id, "OLD", "Old item", "pcs")
    service.record_purchase(owner_id, "OLD", "2", "3.00", date(2026, 6, 1))

    with pytest.raises(ValidationError, match="still has"):
        service.archive_product(owner_id, "OLD")

    service.record_sale(owner_id, "OLD", "2", "5.00", date(2026, 6, 2))
    service.archive_product(owner_id, "OLD")

    assert service.get_stock(owner_id) == []
    with pytest.raises(NotFoundError):
        service.get_stock(owner_id, "OLD")
    with sessions() as session:
        assert session.scalar(select(func.count(PurchaseBatch.id))) == 1
        assert session.scalar(select(func.count(Sale.id))) == 1
        assert session.scalar(select(func.count(JournalEntry.id))) == 3

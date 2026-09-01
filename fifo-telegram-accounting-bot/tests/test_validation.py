from __future__ import annotations

from datetime import date

import pytest

from fifo_accounting_bot.bot.parsers import parse_add_product, parse_sale
from fifo_accounting_bot.exceptions import DuplicateError, ValidationError


def test_duplicate_sku_is_case_insensitive(inventory):
    service, _ = inventory
    service.add_product(1, "abc", "First", "pcs")
    with pytest.raises(DuplicateError):
        service.add_product(1, "ABC", "Second", "pcs")


@pytest.mark.parametrize("quantity", ["0", "-1", "NaN", "Infinity"])
def test_purchase_rejects_non_positive_or_non_finite_quantity(inventory, quantity):
    service, _ = inventory
    service.add_product(1, "ABC", "Item", "pcs")
    with pytest.raises(ValidationError):
        service.record_purchase(1, "ABC", quantity, "2")


def test_add_product_parser_preserves_spaces_in_name():
    parsed = parse_add_product("COFFEE-1 | Arabica coffee beans | kg")
    assert parsed.sku == "COFFEE-1"
    assert parsed.name == "Arabica coffee beans"
    assert parsed.unit == "kg"


def test_sale_parser_accepts_date_without_price():
    parsed = parse_sale("ABC 2 2026-08-30")
    assert parsed.unit_sale_price is None
    assert parsed.sold_on == date(2026, 8, 30)

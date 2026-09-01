from datetime import date
from decimal import Decimal

import pytest

from fifo_accounting_bot.exceptions import ValidationError
from fifo_accounting_bot.services.accounting import AccountingService


def test_quick_income_expense_and_reports_are_double_entry_balanced(inventory):
    inventory_service, session_factory = inventory
    accounting = AccountingService(session_factory)

    accounting.record_income(7, "Consulting", "1000", received_on=date(2026, 8, 1))
    accounting.record_expense(
        7, "August rent", "250", category="rent", paid_on=date(2026, 8, 2)
    )

    trial = accounting.trial_balance(7, date(2026, 8, 31))
    profit = accounting.profit_and_loss(7, date(2026, 8, 1), date(2026, 8, 31))
    balance = accounting.balance_sheet(7, date(2026, 8, 31))

    assert trial.total_debits == trial.total_credits == Decimal("1000.0000")
    assert profit.total_income == Decimal("1000.0000")
    assert profit.total_expenses == Decimal("250.0000")
    assert profit.net_profit == Decimal("750.0000")
    assert balance.total_assets == Decimal("750.0000")
    assert balance.total_liabilities + balance.total_equity == Decimal("750.0000")


def test_invoice_bill_partial_payments_and_open_items(inventory):
    _, session_factory = inventory
    accounting = AccountingService(session_factory)
    customer = accounting.add_contact(8, "customer", "Northwind")
    supplier = accounting.add_contact(8, "supplier", "Contoso Supplies")

    invoice = accounting.create_document(
        8,
        "invoice",
        customer.id,
        "Design services",
        "1000",
        tax_rate="20",
        issue_date=date(2026, 8, 1),
        due_date=date(2026, 8, 31),
    )
    bill = accounting.create_document(
        8,
        "bill",
        supplier.id,
        "Office materials",
        "200",
        tax_rate="10",
        issue_date=date(2026, 8, 2),
        due_date=date(2026, 8, 20),
        expense_category="office",
    )
    paid_invoice = accounting.record_document_payment(
        8, invoice.id, "400", paid_on=date(2026, 8, 5), account_code="1010"
    )
    paid_bill = accounting.record_document_payment(
        8, bill.id, bill.total, paid_on=date(2026, 8, 6), account_code="1010"
    )

    receivables = accounting.open_items(8, "invoice", date(2026, 8, 31))
    payables = accounting.open_items(8, "bill", date(2026, 8, 31))

    assert invoice.total == Decimal("1200.0000")
    assert paid_invoice.status == "partial"
    assert paid_invoice.outstanding == Decimal("800.0000")
    assert paid_bill.status == "paid"
    assert receivables.total_outstanding == Decimal("800.0000")
    assert payables.total_outstanding == Decimal("0.0000")


def test_reversal_preserves_audit_trail_and_cancels_effect(inventory):
    _, session_factory = inventory
    accounting = AccountingService(session_factory)
    original = accounting.record_expense(9, "Duplicate taxi", "50", category="travel")

    reversal = accounting.reverse_transaction(9, original.id, "Entered twice")
    profit = accounting.profit_and_loss(9, date(2026, 1, 1), date(2026, 12, 31))
    history = accounting.recent_transactions(9, 10)

    assert reversal.kind == "reversal"
    assert profit.total_expenses == Decimal("0.0000")
    assert len(history) == 2
    assert {item.status for item in history} == {"posted", "reversed"}
    with pytest.raises(ValidationError):
        accounting.reverse_transaction(9, original.id, "Again")


def test_fifo_journal_is_synchronized_into_general_ledger(inventory):
    inventory_service, session_factory = inventory
    inventory_service.add_product(10, "A", "Widget")
    inventory_service.record_purchase(10, "A", "5", "4", date(2026, 8, 1))
    inventory_service.record_sale(10, "A", "2", "10", date(2026, 8, 2))

    accounting = AccountingService(session_factory)
    profit = accounting.profit_and_loss(10, date(2026, 8, 1), date(2026, 8, 31))
    balance = accounting.balance_sheet(10, date(2026, 8, 31))

    assert profit.total_income == Decimal("20.0000")
    assert profit.total_expenses == Decimal("8.0000")
    assert profit.net_profit == Decimal("12.0000")
    assert balance.total_assets == Decimal("32.0000")
    assert balance.total_liabilities == Decimal("20.0000")
    assert balance.total_equity == Decimal("12.0000")

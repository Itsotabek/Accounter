from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AccountResult:
    id: int
    code: str
    name: str
    account_type: str
    subtype: str


@dataclass(frozen=True, slots=True)
class ContactResult:
    id: int
    contact_type: str
    display_name: str
    email: str | None
    phone: str | None
    tax_id: str | None


@dataclass(frozen=True, slots=True)
class TransactionResult:
    id: int
    transaction_date: date
    kind: str
    description: str
    reference: str
    amount: Decimal
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentResult:
    id: int
    document_type: str
    number: str
    contact_id: int
    contact_name: str
    issue_date: date
    due_date: date
    description: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    paid_amount: Decimal
    outstanding: Decimal
    status: str


@dataclass(frozen=True, slots=True)
class AccountBalance:
    code: str
    name: str
    account_type: str
    debit: Decimal
    credit: Decimal
    balance: Decimal


@dataclass(frozen=True, slots=True)
class TrialBalanceReport:
    as_of: date
    accounts: tuple[AccountBalance, ...]
    total_debits: Decimal
    total_credits: Decimal


@dataclass(frozen=True, slots=True)
class ProfitLossReport:
    period_start: date
    period_end: date
    income: tuple[AccountBalance, ...]
    expenses: tuple[AccountBalance, ...]
    total_income: Decimal
    total_expenses: Decimal
    net_profit: Decimal


@dataclass(frozen=True, slots=True)
class BalanceSheetReport:
    as_of: date
    assets: tuple[AccountBalance, ...]
    liabilities: tuple[AccountBalance, ...]
    equity: tuple[AccountBalance, ...]
    total_assets: Decimal
    total_liabilities: Decimal
    recorded_equity: Decimal
    current_earnings: Decimal
    total_equity: Decimal


@dataclass(frozen=True, slots=True)
class OpenItemsReport:
    as_of: date
    documents: tuple[DocumentResult, ...]
    total_outstanding: Decimal


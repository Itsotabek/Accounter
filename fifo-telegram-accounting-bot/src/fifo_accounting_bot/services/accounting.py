from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fifo_accounting_bot.accounting_schemas import (
    AccountBalance,
    AccountResult,
    BalanceSheetReport,
    ContactResult,
    DocumentResult,
    OpenItemsReport,
    ProfitLossReport,
    TransactionResult,
    TrialBalanceReport,
)
from fifo_accounting_bot.database import SessionFactory
from fifo_accounting_bot.exceptions import DuplicateError, NotFoundError, ValidationError
from fifo_accounting_bot.models import (
    Account,
    AccountingDocument,
    Contact,
    JournalEntry,
    LedgerLine,
    LedgerTransaction,
    Payment,
)

MONEY_SCALE = Decimal("0.0001")
MAX_STORED_VALUE = Decimal("99999999999999.9999")

DEFAULT_ACCOUNTS: tuple[tuple[str, str, str, str], ...] = (
    ("1000", "Cash", "asset", "cash"),
    ("1010", "Bank", "asset", "bank"),
    ("1100", "Accounts Receivable", "asset", "receivable"),
    ("1200", "Inventory", "asset", "inventory"),
    ("1300", "Tax Receivable", "asset", "tax_receivable"),
    ("1500", "Equipment", "asset", "fixed_asset"),
    ("1590", "Accumulated Depreciation", "asset", "contra_asset"),
    ("2000", "Accounts Payable", "liability", "payable"),
    ("2100", "Tax Payable", "liability", "tax_payable"),
    ("2200", "Loans Payable", "liability", "loan"),
    ("3000", "Owner's Equity", "equity", "equity"),
    ("3100", "Owner Drawings", "equity", "contra_equity"),
    ("4000", "Product Sales", "income", "sales"),
    ("4100", "Service Revenue", "income", "service_revenue"),
    ("4200", "Other Income", "income", "other_income"),
    ("5000", "Cost of Goods Sold", "expense", "cogs"),
    ("6000", "Rent Expense", "expense", "rent"),
    ("6010", "Utilities Expense", "expense", "utilities"),
    ("6020", "Wages Expense", "expense", "wages"),
    ("6030", "Marketing Expense", "expense", "marketing"),
    ("6040", "Travel Expense", "expense", "travel"),
    ("6050", "Office Supplies Expense", "expense", "office_supplies"),
    ("6060", "Bank Fees Expense", "expense", "bank_fees"),
    ("6070", "Depreciation Expense", "expense", "depreciation"),
    ("6990", "Other Operating Expense", "expense", "other_expense"),
)

LEGACY_ACCOUNT_CODES = {
    "Inventory": "1200",
    "Accounts Payable": "2000",
    "Cost of Goods Sold": "5000",
    "Cash / Accounts Receivable": "1000",
    "Sales Revenue": "4000",
}

EXPENSE_ACCOUNTS = {
    "rent": "6000",
    "utilities": "6010",
    "wages": "6020",
    "marketing": "6030",
    "travel": "6040",
    "office": "6050",
    "bank_fees": "6060",
    "depreciation": "6070",
    "other": "6990",
}


def _money(value: Decimal | str | int, field: str = "Amount", *, allow_zero: bool = False) -> Decimal:
    try:
        result = Decimal(value).quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field} must be a valid number.") from exc
    if not result.is_finite():
        raise ValidationError(f"{field} must be finite.")
    if result < 0 or (result == 0 and not allow_zero):
        comparison = "zero or greater" if allow_zero else "greater than zero"
        raise ValidationError(f"{field} must be {comparison}.")
    if result > MAX_STORED_VALUE:
        raise ValidationError(f"{field} is too large.")
    return result


def _signed(value: Decimal | str | int, field: str = "Amount") -> Decimal:
    try:
        result = Decimal(value).quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{field} must be a valid number.") from exc
    if not result.is_finite() or abs(result) > MAX_STORED_VALUE:
        raise ValidationError(f"{field} is outside the supported range.")
    return result


class AccountingService:
    """Jurisdiction-neutral double-entry bookkeeping and financial reports."""

    def __init__(self, session_factory: SessionFactory):
        self._sessions = session_factory

    @property
    def session_factory(self) -> SessionFactory:
        return self._sessions

    def initialize_owner(self, owner_id: int) -> None:
        with self._sessions.begin() as session:
            self._ensure_accounts(session, owner_id)
            self._sync_legacy_entries(session, owner_id)

    def list_accounts(
        self, owner_id: int, account_type: str | None = None
    ) -> list[AccountResult]:
        self.initialize_owner(owner_id)
        statement = select(Account).where(
            Account.owner_id == owner_id, Account.is_active.is_(True)
        )
        if account_type:
            statement = statement.where(Account.account_type == account_type)
        statement = statement.order_by(Account.code)
        with self._sessions() as session:
            accounts = list(session.scalars(statement))
        return [self._account_result(item) for item in accounts]

    def add_contact(
        self,
        owner_id: int,
        contact_type: str,
        display_name: str,
        *,
        email: str | None = None,
        phone: str | None = None,
        tax_id: str | None = None,
        notes: str = "",
    ) -> ContactResult:
        normalized_type = contact_type.strip().lower()
        if normalized_type not in {"customer", "supplier", "both"}:
            raise ValidationError("Contact type must be customer, supplier, or both.")
        name = display_name.strip()
        if not name or len(name) > 200:
            raise ValidationError("Contact name must contain 1 to 200 characters.")
        clean_email = email.strip() if email else None
        clean_phone = phone.strip() if phone else None
        clean_tax_id = tax_id.strip() if tax_id else None
        if clean_email and (len(clean_email) > 254 or "@" not in clean_email):
            raise ValidationError("Email address is not valid.")
        if clean_phone and len(clean_phone) > 50:
            raise ValidationError("Phone number is too long.")
        if clean_tax_id and len(clean_tax_id) > 80:
            raise ValidationError("Tax ID is too long.")
        if len(notes) > 2000:
            raise ValidationError("Contact notes are too long.")

        with self._sessions.begin() as session:
            duplicate = session.scalar(
                select(Contact.id).where(
                    Contact.owner_id == owner_id,
                    func.lower(Contact.display_name) == name.lower(),
                    Contact.is_active.is_(True),
                )
            )
            if duplicate:
                raise DuplicateError(f"Contact {name} already exists.")
            contact = Contact(
                owner_id=owner_id,
                contact_type=normalized_type,
                display_name=name,
                email=clean_email,
                phone=clean_phone,
                tax_id=clean_tax_id,
                notes=notes.strip(),
            )
            session.add(contact)
            session.flush()
            return self._contact_result(contact)

    def list_contacts(
        self, owner_id: int, contact_type: str | None = None
    ) -> list[ContactResult]:
        statement = select(Contact).where(
            Contact.owner_id == owner_id, Contact.is_active.is_(True)
        )
        if contact_type in {"customer", "supplier"}:
            statement = statement.where(
                Contact.contact_type.in_((contact_type, "both"))
            )
        statement = statement.order_by(Contact.display_name)
        with self._sessions() as session:
            contacts = list(session.scalars(statement))
        return [self._contact_result(item) for item in contacts]

    def record_income(
        self,
        owner_id: int,
        description: str,
        amount: Decimal | str | int,
        *,
        received_on: date | None = None,
        deposited_to: str = "1000",
        revenue_account: str = "4100",
        reference: str = "",
    ) -> TransactionResult:
        clean_description = self._description(description)
        normalized_amount = _money(amount)
        with self._sessions.begin() as session:
            self._ensure_accounts(session, owner_id)
            self._require_account(session, owner_id, deposited_to, {"cash", "bank"})
            self._require_account_type(session, owner_id, revenue_account, "income")
            transaction = self._post(
                session,
                owner_id,
                received_on or date.today(),
                "quick_income",
                clean_description,
                [(deposited_to, normalized_amount, Decimal("0")),
                 (revenue_account, Decimal("0"), normalized_amount)],
                reference=reference,
            )
            return self._transaction_result(transaction, normalized_amount)

    def record_expense(
        self,
        owner_id: int,
        description: str,
        amount: Decimal | str | int,
        *,
        category: str = "other",
        paid_on: date | None = None,
        paid_from: str = "1000",
        reference: str = "",
    ) -> TransactionResult:
        clean_description = self._description(description)
        normalized_amount = _money(amount)
        expense_code = EXPENSE_ACCOUNTS.get(category.strip().lower())
        if expense_code is None:
            raise ValidationError("Unknown expense category.")
        with self._sessions.begin() as session:
            self._ensure_accounts(session, owner_id)
            self._require_account(session, owner_id, paid_from, {"cash", "bank"})
            transaction = self._post(
                session,
                owner_id,
                paid_on or date.today(),
                "quick_expense",
                clean_description,
                [(expense_code, normalized_amount, Decimal("0")),
                 (paid_from, Decimal("0"), normalized_amount)],
                reference=reference,
            )
            return self._transaction_result(transaction, normalized_amount)

    def create_document(
        self,
        owner_id: int,
        document_type: str,
        contact_id: int,
        description: str,
        subtotal: Decimal | str | int,
        *,
        tax_rate: Decimal | str | int = Decimal("0"),
        issue_date: date | None = None,
        due_date: date | None = None,
        expense_category: str = "other",
    ) -> DocumentResult:
        normalized_type = document_type.strip().lower()
        if normalized_type not in {"invoice", "bill"}:
            raise ValidationError("Document type must be invoice or bill.")
        clean_description = self._description(description)
        normalized_subtotal = _money(subtotal, "Subtotal")
        normalized_rate = _money(tax_rate, "Tax rate", allow_zero=True)
        if normalized_rate > 100:
            raise ValidationError("Tax rate cannot exceed 100%.")
        tax_amount = _money(
            normalized_subtotal * normalized_rate / Decimal("100"),
            "Tax amount",
            allow_zero=True,
        )
        total = _money(normalized_subtotal + tax_amount)
        issued = issue_date or date.today()
        due = due_date or issued
        if due < issued:
            raise ValidationError("Due date cannot be before the issue date.")

        with self._sessions.begin() as session:
            self._ensure_accounts(session, owner_id)
            contact = self._get_contact(session, owner_id, contact_id)
            required_role = "customer" if normalized_type == "invoice" else "supplier"
            if contact.contact_type not in {required_role, "both"}:
                raise ValidationError(
                    f"Choose a {required_role} contact for this document."
                )
            number = self._next_document_number(session, owner_id, normalized_type, issued)
            if normalized_type == "invoice":
                lines = [
                    ("1100", total, Decimal("0")),
                    ("4100", Decimal("0"), normalized_subtotal),
                ]
                if tax_amount:
                    lines.append(("2100", Decimal("0"), tax_amount))
            else:
                expense_code = EXPENSE_ACCOUNTS.get(expense_category.strip().lower())
                if expense_code is None:
                    raise ValidationError("Unknown expense category.")
                lines = [
                    (expense_code, normalized_subtotal, Decimal("0")),
                    ("2000", Decimal("0"), total),
                ]
                if tax_amount:
                    lines.append(("1300", tax_amount, Decimal("0")))
            transaction = self._post(
                session,
                owner_id,
                issued,
                normalized_type,
                f"{number}: {clean_description}",
                lines,
                reference=number,
                contact_id=contact.id,
            )
            document = AccountingDocument(
                owner_id=owner_id,
                document_type=normalized_type,
                number=number,
                contact_id=contact.id,
                issue_date=issued,
                due_date=due,
                description=clean_description,
                subtotal=normalized_subtotal,
                tax_amount=tax_amount,
                total=total,
                paid_amount=Decimal("0"),
                status="open",
                transaction_id=transaction.id,
            )
            session.add(document)
            session.flush()
            return self._document_result(document, contact.display_name, Decimal("0"))

    def list_open_documents(
        self, owner_id: int, document_type: str
    ) -> list[DocumentResult]:
        normalized_type = document_type.strip().lower()
        if normalized_type not in {"invoice", "bill"}:
            raise ValidationError("Document type must be invoice or bill.")
        statement = (
            select(AccountingDocument, Contact.display_name)
            .join(Contact, Contact.id == AccountingDocument.contact_id)
            .where(
                AccountingDocument.owner_id == owner_id,
                AccountingDocument.document_type == normalized_type,
                AccountingDocument.status.in_(("open", "partial")),
            )
            .order_by(AccountingDocument.due_date, AccountingDocument.id)
        )
        with self._sessions() as session:
            rows = session.execute(statement).all()
        return [
            self._document_result(document, name, document.paid_amount)
            for document, name in rows
        ]

    def record_document_payment(
        self,
        owner_id: int,
        document_id: int,
        amount: Decimal | str | int,
        *,
        paid_on: date | None = None,
        account_code: str = "1000",
        reference: str = "",
    ) -> DocumentResult:
        normalized_amount = _money(amount)
        payment_date = paid_on or date.today()
        with self._sessions.begin() as session:
            self._ensure_accounts(session, owner_id)
            self._require_account(session, owner_id, account_code, {"cash", "bank"})
            document = session.scalar(
                select(AccountingDocument)
                .where(
                    AccountingDocument.id == document_id,
                    AccountingDocument.owner_id == owner_id,
                )
                .with_for_update()
            )
            if document is None:
                raise NotFoundError("Invoice or bill was not found.")
            outstanding = _money(
                Decimal(document.total) - Decimal(document.paid_amount),
                "Outstanding amount",
                allow_zero=True,
            )
            if outstanding == 0:
                raise ValidationError(f"{document.number} is already fully paid.")
            if normalized_amount > outstanding:
                raise ValidationError(
                    f"Payment cannot exceed the outstanding amount {outstanding}."
                )
            if document.document_type == "invoice":
                direction = "received"
                lines = [
                    (account_code, normalized_amount, Decimal("0")),
                    ("1100", Decimal("0"), normalized_amount),
                ]
                kind = "invoice_payment"
            else:
                direction = "paid"
                lines = [
                    ("2000", normalized_amount, Decimal("0")),
                    (account_code, Decimal("0"), normalized_amount),
                ]
                kind = "bill_payment"
            transaction = self._post(
                session,
                owner_id,
                payment_date,
                kind,
                f"Payment for {document.number}",
                lines,
                reference=reference or document.number,
                contact_id=document.contact_id,
            )
            payment = Payment(
                owner_id=owner_id,
                document_id=document.id,
                paid_on=payment_date,
                amount=normalized_amount,
                account_code=account_code,
                reference=reference.strip(),
                direction=direction,
                transaction_id=transaction.id,
            )
            session.add(payment)
            document.paid_amount = _money(
                Decimal(document.paid_amount) + normalized_amount,
                "Paid amount",
                allow_zero=True,
            )
            document.status = (
                "paid" if Decimal(document.paid_amount) == Decimal(document.total) else "partial"
            )
            contact_name = session.scalar(
                select(Contact.display_name).where(Contact.id == document.contact_id)
            ) or "Unknown"
            return self._document_result(
                document, contact_name, Decimal(document.paid_amount)
            )

    def record_transfer(
        self,
        owner_id: int,
        amount: Decimal | str | int,
        from_account: str,
        to_account: str,
        *,
        transferred_on: date | None = None,
        description: str = "Cash transfer",
    ) -> TransactionResult:
        normalized_amount = _money(amount)
        if from_account == to_account:
            raise ValidationError("Transfer accounts must be different.")
        clean_description = self._description(description)
        with self._sessions.begin() as session:
            self._ensure_accounts(session, owner_id)
            self._require_account(session, owner_id, from_account, {"cash", "bank"})
            self._require_account(session, owner_id, to_account, {"cash", "bank"})
            transaction = self._post(
                session,
                owner_id,
                transferred_on or date.today(),
                "transfer",
                clean_description,
                [(to_account, normalized_amount, Decimal("0")),
                 (from_account, Decimal("0"), normalized_amount)],
            )
            return self._transaction_result(transaction, normalized_amount)

    def record_manual_journal(
        self,
        owner_id: int,
        description: str,
        amount: Decimal | str | int,
        debit_account: str,
        credit_account: str,
        *,
        entry_date: date | None = None,
        reference: str = "",
    ) -> TransactionResult:
        normalized_amount = _money(amount)
        clean_description = self._description(description)
        if debit_account == credit_account:
            raise ValidationError("Debit and credit accounts must be different.")
        with self._sessions.begin() as session:
            self._ensure_accounts(session, owner_id)
            self._require_account(session, owner_id, debit_account)
            self._require_account(session, owner_id, credit_account)
            transaction = self._post(
                session,
                owner_id,
                entry_date or date.today(),
                "manual_journal",
                clean_description,
                [(debit_account, normalized_amount, Decimal("0")),
                 (credit_account, Decimal("0"), normalized_amount)],
                reference=reference,
            )
            return self._transaction_result(transaction, normalized_amount)

    def recent_transactions(
        self, owner_id: int, limit: int = 12, *, reversible_only: bool = False
    ) -> list[TransactionResult]:
        self.initialize_owner(owner_id)
        safe_limit = max(1, min(limit, 50))
        statement = (
            select(LedgerTransaction, func.coalesce(func.sum(LedgerLine.debit), 0))
            .join(LedgerLine, LedgerLine.transaction_id == LedgerTransaction.id)
            .where(LedgerTransaction.owner_id == owner_id)
            .group_by(LedgerTransaction.id)
            .order_by(
                LedgerTransaction.transaction_date.desc(),
                LedgerTransaction.id.desc(),
            )
        )
        if reversible_only:
            statement = statement.where(
                LedgerTransaction.kind.in_(
                    ("quick_income", "quick_expense", "transfer", "manual_journal")
                ),
                LedgerTransaction.status == "posted",
                LedgerTransaction.reversal_of_id.is_(None),
            )
        statement = statement.limit(safe_limit)
        with self._sessions() as session:
            rows = session.execute(statement).all()
        return [self._transaction_result(item, Decimal(amount)) for item, amount in rows]

    def reverse_transaction(
        self,
        owner_id: int,
        transaction_id: int,
        reason: str,
        *,
        reversal_date: date | None = None,
    ) -> TransactionResult:
        clean_reason = self._description(reason)
        with self._sessions.begin() as session:
            self._ensure_accounts(session, owner_id)
            transaction = session.scalar(
                select(LedgerTransaction)
                .where(
                    LedgerTransaction.id == transaction_id,
                    LedgerTransaction.owner_id == owner_id,
                )
                .with_for_update()
            )
            if transaction is None:
                raise NotFoundError("Transaction was not found.")
            if transaction.kind not in {
                "quick_income", "quick_expense", "transfer", "manual_journal"
            }:
                raise ValidationError(
                    "This transaction needs its specialized correction workflow."
                )
            if transaction.status != "posted" or transaction.reversal_of_id is not None:
                raise ValidationError("This transaction cannot be reversed again.")
            already_reversed = session.scalar(
                select(LedgerTransaction.id).where(
                    LedgerTransaction.owner_id == owner_id,
                    LedgerTransaction.reversal_of_id == transaction.id,
                )
            )
            if already_reversed:
                raise ValidationError("This transaction has already been reversed.")
            source_lines = list(
                session.scalars(
                    select(LedgerLine).where(
                        LedgerLine.transaction_id == transaction.id
                    )
                )
            )
            codes = dict(
                session.execute(
                    select(Account.id, Account.code).where(Account.owner_id == owner_id)
                ).all()
            )
            reversal_lines = [
                (codes[line.account_id], Decimal(line.credit), Decimal(line.debit))
                for line in source_lines
            ]
            amount = sum((Decimal(line.credit) for line in source_lines), Decimal("0"))
            reversal = self._post(
                session,
                owner_id,
                reversal_date or date.today(),
                "reversal",
                f"Reversal of #{transaction.id}: {clean_reason}",
                reversal_lines,
                reference=f"REV-{transaction.id}",
                source_key=f"reversal:{transaction.id}",
                reversal_of_id=transaction.id,
            )
            transaction.status = "reversed"
            return self._transaction_result(reversal, amount)

    def trial_balance(self, owner_id: int, as_of: date | None = None) -> TrialBalanceReport:
        report_date = as_of or date.today()
        accounts, movements = self._movements(owner_id, None, report_date)
        rows: list[AccountBalance] = []
        total_debits = Decimal("0")
        total_credits = Decimal("0")
        for account in accounts:
            debit, credit = movements[account.id]
            net = _signed(debit - credit)
            ending_debit = net if net > 0 else Decimal("0")
            ending_credit = -net if net < 0 else Decimal("0")
            if ending_debit or ending_credit:
                rows.append(
                    AccountBalance(
                        account.code,
                        account.name,
                        account.account_type,
                        ending_debit,
                        ending_credit,
                        net,
                    )
                )
                total_debits += ending_debit
                total_credits += ending_credit
        return TrialBalanceReport(
            report_date,
            tuple(rows),
            _money(total_debits, allow_zero=True),
            _money(total_credits, allow_zero=True),
        )

    def profit_and_loss(
        self, owner_id: int, period_start: date, period_end: date
    ) -> ProfitLossReport:
        if period_start > period_end:
            raise ValidationError("Report start date cannot be after the end date.")
        accounts, movements = self._movements(owner_id, period_start, period_end)
        income_rows: list[AccountBalance] = []
        expense_rows: list[AccountBalance] = []
        for account in accounts:
            debit, credit = movements[account.id]
            if account.account_type == "income":
                natural = _signed(credit - debit)
                if natural:
                    income_rows.append(
                        AccountBalance(account.code, account.name, account.account_type, debit, credit, natural)
                    )
            elif account.account_type == "expense":
                natural = _signed(debit - credit)
                if natural:
                    expense_rows.append(
                        AccountBalance(account.code, account.name, account.account_type, debit, credit, natural)
                    )
        total_income = _signed(sum((row.balance for row in income_rows), Decimal("0")))
        total_expenses = _signed(sum((row.balance for row in expense_rows), Decimal("0")))
        return ProfitLossReport(
            period_start,
            period_end,
            tuple(income_rows),
            tuple(expense_rows),
            total_income,
            total_expenses,
            _signed(total_income - total_expenses),
        )

    def balance_sheet(self, owner_id: int, as_of: date | None = None) -> BalanceSheetReport:
        report_date = as_of or date.today()
        accounts, movements = self._movements(owner_id, None, report_date)
        assets: list[AccountBalance] = []
        liabilities: list[AccountBalance] = []
        equity: list[AccountBalance] = []
        current_earnings = Decimal("0")
        for account in accounts:
            debit, credit = movements[account.id]
            if account.account_type == "asset":
                natural = _signed(debit - credit)
                if natural:
                    assets.append(AccountBalance(account.code, account.name, account.account_type, debit, credit, natural))
            elif account.account_type in {"liability", "equity"}:
                natural = _signed(credit - debit)
                if natural:
                    target = liabilities if account.account_type == "liability" else equity
                    target.append(AccountBalance(account.code, account.name, account.account_type, debit, credit, natural))
            elif account.account_type == "income":
                current_earnings += credit - debit
            elif account.account_type == "expense":
                current_earnings -= debit - credit
        total_assets = _signed(sum((row.balance for row in assets), Decimal("0")))
        total_liabilities = _signed(sum((row.balance for row in liabilities), Decimal("0")))
        recorded_equity = _signed(sum((row.balance for row in equity), Decimal("0")))
        current_earnings = _signed(current_earnings)
        return BalanceSheetReport(
            report_date,
            tuple(assets),
            tuple(liabilities),
            tuple(equity),
            total_assets,
            total_liabilities,
            recorded_equity,
            current_earnings,
            _signed(recorded_equity + current_earnings),
        )

    def open_items(
        self, owner_id: int, document_type: str, as_of: date | None = None
    ) -> OpenItemsReport:
        report_date = as_of or date.today()
        normalized_type = document_type.strip().lower()
        if normalized_type not in {"invoice", "bill"}:
            raise ValidationError("Document type must be invoice or bill.")
        statement = (
            select(AccountingDocument, Contact.display_name)
            .join(Contact, Contact.id == AccountingDocument.contact_id)
            .where(
                AccountingDocument.owner_id == owner_id,
                AccountingDocument.document_type == normalized_type,
                AccountingDocument.issue_date <= report_date,
            )
            .order_by(AccountingDocument.due_date, AccountingDocument.id)
        )
        with self._sessions() as session:
            rows = session.execute(statement).all()
            results: list[DocumentResult] = []
            for document, name in rows:
                paid = session.scalar(
                    select(func.coalesce(func.sum(Payment.amount), 0)).where(
                        Payment.document_id == document.id,
                        Payment.paid_on <= report_date,
                    )
                )
                paid_decimal = Decimal(paid or 0)
                if paid_decimal < Decimal(document.total):
                    results.append(self._document_result(document, name, paid_decimal))
        total = _money(sum((item.outstanding for item in results), Decimal("0")), allow_zero=True)
        return OpenItemsReport(report_date, tuple(results), total)

    def cash_balances(self, owner_id: int, as_of: date | None = None) -> tuple[AccountBalance, ...]:
        report_date = as_of or date.today()
        accounts, movements = self._movements(owner_id, None, report_date)
        rows = []
        for account in accounts:
            if account.subtype not in {"cash", "bank"}:
                continue
            debit, credit = movements[account.id]
            rows.append(
                AccountBalance(
                    account.code,
                    account.name,
                    account.account_type,
                    debit,
                    credit,
                    _signed(debit - credit),
                )
            )
        return tuple(rows)

    def _movements(
        self, owner_id: int, period_start: date | None, period_end: date
    ) -> tuple[list[Account], defaultdict[int, tuple[Decimal, Decimal]]]:
        self.initialize_owner(owner_id)
        with self._sessions() as session:
            accounts = list(
                session.scalars(
                    select(Account)
                    .where(Account.owner_id == owner_id)
                    .order_by(Account.code)
                )
            )
            statement = (
                select(LedgerLine.account_id, LedgerLine.debit, LedgerLine.credit)
                .join(
                    LedgerTransaction,
                    LedgerTransaction.id == LedgerLine.transaction_id,
                )
                .where(
                    LedgerTransaction.owner_id == owner_id,
                    LedgerTransaction.transaction_date <= period_end,
                )
            )
            if period_start:
                statement = statement.where(
                    LedgerTransaction.transaction_date >= period_start
                )
            rows = session.execute(statement).all()
        movements: defaultdict[int, tuple[Decimal, Decimal]] = defaultdict(
            lambda: (Decimal("0"), Decimal("0"))
        )
        for account_id, debit, credit in rows:
            old_debit, old_credit = movements[account_id]
            movements[account_id] = (
                old_debit + Decimal(debit),
                old_credit + Decimal(credit),
            )
        return accounts, movements

    def _ensure_accounts(self, session: Session, owner_id: int) -> None:
        existing = set(
            session.scalars(
                select(Account.code).where(Account.owner_id == owner_id)
            )
        )
        for code, name, account_type, subtype in DEFAULT_ACCOUNTS:
            if code not in existing:
                session.add(
                    Account(
                        owner_id=owner_id,
                        code=code,
                        name=name,
                        account_type=account_type,
                        subtype=subtype,
                    )
                )
        session.flush()

    def _sync_legacy_entries(self, session: Session, owner_id: int) -> None:
        entries = list(
            session.scalars(
                select(JournalEntry)
                .where(JournalEntry.owner_id == owner_id)
                .order_by(JournalEntry.id)
            )
        )
        existing = set(
            session.scalars(
                select(LedgerTransaction.source_key).where(
                    LedgerTransaction.owner_id == owner_id,
                    LedgerTransaction.source_key.is_not(None),
                )
            )
        )
        for entry in entries:
            source_key = f"legacy:{entry.id}"
            amount = Decimal(entry.amount)
            if source_key in existing or amount <= 0:
                continue
            debit_code = LEGACY_ACCOUNT_CODES.get(entry.debit_account)
            credit_code = LEGACY_ACCOUNT_CODES.get(entry.credit_account)
            if debit_code is None or credit_code is None:
                continue
            self._post(
                session,
                owner_id,
                entry.entry_date,
                f"inventory_{entry.reference_type}",
                entry.memo or entry.reference_type,
                [(debit_code, amount, Decimal("0")),
                 (credit_code, Decimal("0"), amount)],
                reference=f"{entry.reference_type}:{entry.reference_id}",
                source_key=source_key,
            )

    def _post(
        self,
        session: Session,
        owner_id: int,
        transaction_date: date,
        kind: str,
        description: str,
        lines: list[tuple[str, Decimal, Decimal]],
        *,
        reference: str = "",
        source_key: str | None = None,
        contact_id: int | None = None,
        reversal_of_id: int | None = None,
    ) -> LedgerTransaction:
        total_debit = sum((Decimal(line[1]) for line in lines), Decimal("0"))
        total_credit = sum((Decimal(line[2]) for line in lines), Decimal("0"))
        if total_debit <= 0 or total_debit != total_credit:
            raise ValidationError("Journal entry must have equal positive debits and credits.")
        codes = {line[0] for line in lines}
        accounts = {
            item.code: item
            for item in session.scalars(
                select(Account).where(
                    Account.owner_id == owner_id,
                    Account.code.in_(codes),
                    Account.is_active.is_(True),
                )
            )
        }
        missing = codes - set(accounts)
        if missing:
            raise ValidationError(f"Unknown account code: {sorted(missing)[0]}.")
        transaction = LedgerTransaction(
            owner_id=owner_id,
            transaction_date=transaction_date,
            kind=kind,
            description=description,
            reference=reference.strip()[:100],
            source_key=source_key,
            contact_id=contact_id,
            reversal_of_id=reversal_of_id,
        )
        session.add(transaction)
        session.flush()
        for account_code, debit, credit in lines:
            session.add(
                LedgerLine(
                    transaction_id=transaction.id,
                    account_id=accounts[account_code].id,
                    debit=_money(debit, allow_zero=True),
                    credit=_money(credit, allow_zero=True),
                    memo=description,
                )
            )
        return transaction

    @staticmethod
    def _description(value: str) -> str:
        clean = value.strip()
        if not clean or len(clean) > 300:
            raise ValidationError("Description must contain 1 to 300 characters.")
        return clean

    @staticmethod
    def _account_result(account: Account) -> AccountResult:
        return AccountResult(
            account.id, account.code, account.name, account.account_type, account.subtype
        )

    @staticmethod
    def _contact_result(contact: Contact) -> ContactResult:
        return ContactResult(
            contact.id,
            contact.contact_type,
            contact.display_name,
            contact.email,
            contact.phone,
            contact.tax_id,
        )

    @staticmethod
    def _transaction_result(
        transaction: LedgerTransaction, amount: Decimal
    ) -> TransactionResult:
        return TransactionResult(
            transaction.id,
            transaction.transaction_date,
            transaction.kind,
            transaction.description,
            transaction.reference,
            _money(amount, allow_zero=True),
            transaction.status,
            transaction.created_at,
        )

    @staticmethod
    def _document_result(
        document: AccountingDocument, contact_name: str, paid_amount: Decimal
    ) -> DocumentResult:
        outstanding = _money(
            Decimal(document.total) - paid_amount,
            "Outstanding amount",
            allow_zero=True,
        )
        if outstanding == 0:
            status = "paid"
        elif paid_amount > 0:
            status = "partial"
        else:
            status = "open"
        return DocumentResult(
            document.id,
            document.document_type,
            document.number,
            document.contact_id,
            contact_name,
            document.issue_date,
            document.due_date,
            document.description,
            Decimal(document.subtotal),
            Decimal(document.tax_amount),
            Decimal(document.total),
            paid_amount,
            outstanding,
            status,
        )

    @staticmethod
    def _next_document_number(
        session: Session, owner_id: int, document_type: str, issued: date
    ) -> str:
        count = session.scalar(
            select(func.count(AccountingDocument.id)).where(
                AccountingDocument.owner_id == owner_id,
                AccountingDocument.document_type == document_type,
                AccountingDocument.issue_date >= date(issued.year, 1, 1),
                AccountingDocument.issue_date <= date(issued.year, 12, 31),
            )
        ) or 0
        prefix = "INV" if document_type == "invoice" else "BILL"
        return f"{prefix}-{issued.year}-{int(count) + 1:04d}"

    @staticmethod
    def _get_contact(session: Session, owner_id: int, contact_id: int) -> Contact:
        contact = session.scalar(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.owner_id == owner_id,
                Contact.is_active.is_(True),
            )
        )
        if contact is None:
            raise NotFoundError("Contact was not found.")
        return contact

    @staticmethod
    def _require_account(
        session: Session,
        owner_id: int,
        account_code: str,
        allowed_subtypes: set[str] | None = None,
    ) -> Account:
        account = session.scalar(
            select(Account).where(
                Account.owner_id == owner_id,
                Account.code == account_code,
                Account.is_active.is_(True),
            )
        )
        if account is None:
            raise NotFoundError(f"Account {account_code} was not found.")
        if allowed_subtypes and account.subtype not in allowed_subtypes:
            raise ValidationError("Choose a cash or bank account.")
        return account

    @classmethod
    def _require_account_type(
        cls, session: Session, owner_id: int, account_code: str, account_type: str
    ) -> Account:
        account = cls._require_account(session, owner_id, account_code)
        if account.account_type != account_type:
            raise ValidationError(f"Account {account_code} must be an {account_type} account.")
        return account

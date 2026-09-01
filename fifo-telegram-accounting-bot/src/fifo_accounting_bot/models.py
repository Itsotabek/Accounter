from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("owner_id", "sku", name="uq_products_owner_sku"),
        CheckConstraint("length(sku) > 0", name="ck_products_sku_not_empty"),
        CheckConstraint("length(name) > 0", name="ck_products_name_not_empty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="pcs")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    purchase_batches: Mapped[list["PurchaseBatch"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    sales: Mapped[list["Sale"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ArchivedProduct(Base):
    """Hides a zero-stock product without destroying its accounting history."""

    __tablename__ = "archived_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class TelegramUser(Base):
    """Minimal bot preferences and access state; no Telegram message history."""

    __tablename__ = "telegram_users"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class PurchaseBatch(Base):
    __tablename__ = "purchase_batches"
    __table_args__ = (
        CheckConstraint("original_quantity > 0", name="ck_batches_original_positive"),
        CheckConstraint("remaining_quantity >= 0", name="ck_batches_remaining_nonnegative"),
        CheckConstraint(
            "remaining_quantity <= original_quantity",
            name="ck_batches_remaining_not_over_original",
        ),
        CheckConstraint("unit_cost >= 0", name="ck_batches_cost_nonnegative"),
        Index("ix_batches_fifo", "product_id", "purchased_on", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    purchased_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    original_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    product: Mapped[Product] = relationship(back_populates="purchase_batches")
    allocations: Mapped[list["SaleAllocation"]] = relationship(
        back_populates="purchase_batch"
    )


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sales_quantity_positive"),
        CheckConstraint("revenue IS NULL OR revenue >= 0", name="ck_sales_revenue_nonnegative"),
        CheckConstraint("cogs >= 0", name="ck_sales_cogs_nonnegative"),
        Index("ix_sales_product_date", "product_id", "sold_on"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    sold_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    cogs: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    product: Mapped[Product] = relationship(back_populates="sales")
    allocations: Mapped[list["SaleAllocation"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )


class SaleAllocation(Base):
    """Auditable link between a sale and each FIFO purchase layer it consumed."""

    __tablename__ = "sale_allocations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_allocations_quantity_positive"),
        CheckConstraint("unit_cost >= 0", name="ck_allocations_cost_nonnegative"),
        CheckConstraint("cost >= 0", name="ck_allocations_total_nonnegative"),
        UniqueConstraint("sale_id", "purchase_batch_id", name="uq_sale_batch_allocation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"), nullable=False
    )
    purchase_batch_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_batches.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="allocations")
    purchase_batch: Mapped[PurchaseBatch] = relationship(back_populates="allocations")


class JournalEntry(Base):
    """A balanced journal entry represented by one debit/credit pair."""

    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_journal_amount_nonnegative"),
        CheckConstraint("length(debit_account) > 0", name="ck_journal_debit_not_empty"),
        CheckConstraint("length(credit_account) > 0", name="ck_journal_credit_not_empty"),
        Index("ix_journal_owner_date", "owner_id", "entry_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False)
    debit_account: Mapped[str] = mapped_column(String(100), nullable=False)
    credit_account: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    memo: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class Account(Base):
    """One account in a user's chart of accounts."""

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("owner_id", "code", name="uq_accounts_owner_code"),
        UniqueConstraint("owner_id", "name", name="uq_accounts_owner_name"),
        CheckConstraint(
            "account_type IN ('asset', 'liability', 'equity', 'income', 'expense')",
            name="ck_accounts_type",
        ),
        CheckConstraint("length(code) > 0", name="ck_accounts_code_not_empty"),
        CheckConstraint("length(name) > 0", name="ck_accounts_name_not_empty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subtype: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    lines: Mapped[list["LedgerLine"]] = relationship(back_populates="account")


class Contact(Base):
    """Customer/supplier master data used by invoices and bills."""

    __tablename__ = "contacts"
    __table_args__ = (
        CheckConstraint(
            "contact_type IN ('customer', 'supplier', 'both')",
            name="ck_contacts_type",
        ),
        CheckConstraint("length(display_name) > 0", name="ck_contacts_name_not_empty"),
        Index("ix_contacts_owner_name", "owner_id", "display_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    contact_type: Mapped[str] = mapped_column(String(16), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    documents: Mapped[list["AccountingDocument"]] = relationship(
        back_populates="contact"
    )


class LedgerTransaction(Base):
    """Auditable double-entry transaction header."""

    __tablename__ = "ledger_transactions"
    __table_args__ = (
        UniqueConstraint("owner_id", "source_key", name="uq_ledger_owner_source"),
        CheckConstraint(
            "status IN ('posted', 'reversed')", name="ck_ledger_transactions_status"
        ),
        Index("ix_ledger_owner_date", "owner_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    reference: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    source_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="posted")
    reversal_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("ledger_transactions.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    lines: Mapped[list["LedgerLine"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )


class LedgerLine(Base):
    """A debit or credit line belonging to a balanced transaction."""

    __tablename__ = "ledger_lines"
    __table_args__ = (
        CheckConstraint("debit >= 0", name="ck_ledger_lines_debit_nonnegative"),
        CheckConstraint("credit >= 0", name="ck_ledger_lines_credit_nonnegative"),
        CheckConstraint(
            "(debit > 0 AND credit = 0) OR (credit > 0 AND debit = 0)",
            name="ck_ledger_lines_one_side",
        ),
        Index("ix_ledger_lines_account", "account_id", "transaction_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("ledger_transactions.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    debit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    memo: Mapped[str] = mapped_column(String(300), nullable=False, default="")

    transaction: Mapped[LedgerTransaction] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship(back_populates="lines")


class AccountingDocument(Base):
    """A simple customer invoice or supplier bill with payment status."""

    __tablename__ = "accounting_documents"
    __table_args__ = (
        UniqueConstraint(
            "owner_id", "document_type", "number", name="uq_documents_owner_type_number"
        ),
        CheckConstraint(
            "document_type IN ('invoice', 'bill')", name="ck_documents_type"
        ),
        CheckConstraint(
            "status IN ('open', 'partial', 'paid')", name="ck_documents_status"
        ),
        CheckConstraint("subtotal >= 0", name="ck_documents_subtotal_nonnegative"),
        CheckConstraint("tax_amount >= 0", name="ck_documents_tax_nonnegative"),
        CheckConstraint("total >= 0", name="ck_documents_total_nonnegative"),
        CheckConstraint("paid_amount >= 0", name="ck_documents_paid_nonnegative"),
        CheckConstraint("paid_amount <= total", name="ck_documents_paid_not_over_total"),
        Index("ix_documents_owner_due", "owner_id", "document_type", "due_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(16), nullable=False)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("ledger_transactions.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    contact: Mapped[Contact] = relationship(back_populates="documents")
    payments: Mapped[list["Payment"]] = relationship(back_populates="document")


class Payment(Base):
    """A receipt against an invoice or a payment against a supplier bill."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint(
            "direction IN ('received', 'paid')", name="ck_payments_direction"
        ),
        Index("ix_payments_owner_date", "owner_id", "paid_on"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_documents.id", ondelete="RESTRICT"), nullable=False
    )
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False)
    reference: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("ledger_transactions.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    document: Mapped[AccountingDocument] = relationship(back_populates="payments")

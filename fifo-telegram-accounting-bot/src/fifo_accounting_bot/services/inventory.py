from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from fifo_accounting_bot.database import SessionFactory
from fifo_accounting_bot.exceptions import (
    DuplicateError,
    InsufficientStockError,
    NotFoundError,
    ValidationError,
)
from fifo_accounting_bot.localization import (
    canonicalize_unit,
    localize_product_name,
    localize_unit,
    product_translations,
)
from fifo_accounting_bot.models import (
    ArchivedProduct,
    JournalEntry,
    Product,
    ProductTranslation,
    PurchaseBatch,
    Sale,
    SaleAllocation,
)
from fifo_accounting_bot.schemas import (
    ActivityLine,
    FifoLayer,
    InventoryReport,
    ProductResult,
    PurchaseResult,
    SaleResult,
    StockLine,
)

QUANTITY_SCALE = Decimal("0.0001")
MONEY_SCALE = Decimal("0.0001")
MAX_STORED_VALUE = Decimal("99999999999999.9999")


def _decimal(value: Decimal | str | int, field: str, *, allow_zero: bool) -> Decimal:
    try:
        result = Decimal(value).quantize(QUANTITY_SCALE, rounding=ROUND_HALF_UP)
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


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)


class InventoryService:
    """Transactional FIFO inventory operations scoped to a Telegram owner ID."""

    def __init__(self, session_factory: SessionFactory):
        self._sessions = session_factory

    @property
    def session_factory(self) -> SessionFactory:
        return self._sessions

    def add_product(
        self,
        owner_id: int,
        sku: str,
        name: str,
        unit: str = "pcs",
        language: str | None = None,
    ) -> ProductResult:
        normalized_sku = sku.strip().upper()
        normalized_name = name.strip()
        normalized_unit = canonicalize_unit(unit)
        if not normalized_sku or len(normalized_sku) > 64:
            raise ValidationError("SKU must contain 1 to 64 characters.")
        if not normalized_name or len(normalized_name) > 200:
            raise ValidationError("Product name must contain 1 to 200 characters.")
        if not normalized_unit or len(normalized_unit) > 32:
            raise ValidationError("Unit must contain 1 to 32 characters.")

        try:
            with self._sessions.begin() as session:
                existing = session.scalar(
                    select(Product).where(
                        Product.owner_id == owner_id,
                        Product.sku == normalized_sku,
                    )
                )
                if existing:
                    archived = session.scalar(
                        select(ArchivedProduct.id).where(
                            ArchivedProduct.product_id == existing.id
                        )
                    )
                    suffix = " and is archived" if archived else ""
                    raise DuplicateError(
                        f"Product {normalized_sku} already exists{suffix}."
                    )
                product = Product(
                    owner_id=owner_id,
                    sku=normalized_sku,
                    name=normalized_name,
                    unit=normalized_unit,
                )
                session.add(product)
                session.flush()
                translations = product_translations(normalized_name)
                if language:
                    translations[language] = normalized_name
                session.add_all(
                    ProductTranslation(
                        product_id=product.id,
                        language=translation_language,
                        name=translation_name,
                    )
                    for translation_language, translation_name in translations.items()
                )
                result = ProductResult(product.id, product.sku, product.name, product.unit)
            return result
        except IntegrityError as exc:
            raise DuplicateError(f"Product {normalized_sku} already exists.") from exc

    def record_purchase(
        self,
        owner_id: int,
        sku: str,
        quantity: Decimal | str | int,
        unit_cost: Decimal | str | int,
        purchased_on: date | None = None,
    ) -> PurchaseResult:
        normalized_sku = sku.strip().upper()
        normalized_quantity = _decimal(quantity, "Quantity", allow_zero=False)
        normalized_cost = _decimal(unit_cost, "Unit cost", allow_zero=True)
        purchase_date = purchased_on or date.today()
        total_cost = _money(normalized_quantity * normalized_cost)
        if total_cost > MAX_STORED_VALUE:
            raise ValidationError("Purchase total is too large.")

        with self._sessions.begin() as session:
            product = self._get_product(session, owner_id, normalized_sku)
            batch = PurchaseBatch(
                product_id=product.id,
                purchased_on=purchase_date,
                original_quantity=normalized_quantity,
                remaining_quantity=normalized_quantity,
                unit_cost=normalized_cost,
            )
            session.add(batch)
            session.flush()
            session.add(
                JournalEntry(
                    owner_id=owner_id,
                    entry_date=purchase_date,
                    reference_type="purchase",
                    reference_id=batch.id,
                    debit_account="Inventory",
                    credit_account="Accounts Payable",
                    amount=total_cost,
                    memo=f"Purchase {normalized_quantity} {product.unit} of {product.sku}",
                )
            )
            result = PurchaseResult(
                batch_id=batch.id,
                sku=product.sku,
                quantity=normalized_quantity,
                unit_cost=normalized_cost,
                total_cost=total_cost,
                purchased_on=purchase_date,
            )
        return result

    def record_sale(
        self,
        owner_id: int,
        sku: str,
        quantity: Decimal | str | int,
        unit_sale_price: Decimal | str | int | None = None,
        sold_on: date | None = None,
    ) -> SaleResult:
        normalized_sku = sku.strip().upper()
        normalized_quantity = _decimal(quantity, "Quantity", allow_zero=False)
        sale_date = sold_on or date.today()
        normalized_price = (
            _decimal(unit_sale_price, "Unit sale price", allow_zero=True)
            if unit_sale_price is not None
            else None
        )
        revenue = (
            _money(normalized_quantity * normalized_price)
            if normalized_price is not None
            else None
        )
        if revenue is not None and revenue > MAX_STORED_VALUE:
            raise ValidationError("Sale revenue is too large.")

        with self._sessions.begin() as session:
            product = self._get_product(session, owner_id, normalized_sku)
            batches = list(
                session.scalars(
                    select(PurchaseBatch)
                    .where(
                        PurchaseBatch.product_id == product.id,
                        PurchaseBatch.remaining_quantity > 0,
                    )
                    .order_by(PurchaseBatch.purchased_on, PurchaseBatch.id)
                    .with_for_update()
                )
            )
            available = sum(
                (batch.remaining_quantity for batch in batches), start=Decimal("0")
            )
            if available < normalized_quantity:
                raise InsufficientStockError(
                    f"Insufficient stock for {normalized_sku}: requested "
                    f"{normalized_quantity}, available {available}."
                )

            sale = Sale(
                product_id=product.id,
                sold_on=sale_date,
                quantity=normalized_quantity,
                revenue=revenue,
                cogs=Decimal("0"),
            )
            session.add(sale)
            session.flush()

            remaining_to_allocate = normalized_quantity
            cogs = Decimal("0")
            layers: list[FifoLayer] = []
            for batch in batches:
                if remaining_to_allocate <= 0:
                    break
                consumed = min(batch.remaining_quantity, remaining_to_allocate)
                layer_cost = _money(consumed * batch.unit_cost)
                batch.remaining_quantity -= consumed
                remaining_to_allocate -= consumed
                cogs += layer_cost
                session.add(
                    SaleAllocation(
                        sale_id=sale.id,
                        purchase_batch_id=batch.id,
                        quantity=consumed,
                        unit_cost=batch.unit_cost,
                        cost=layer_cost,
                    )
                )
                layers.append(
                    FifoLayer(
                        batch_id=batch.id,
                        purchased_on=batch.purchased_on,
                        quantity=consumed,
                        unit_cost=batch.unit_cost,
                        cost=layer_cost,
                    )
                )

            cogs = _money(cogs)
            if cogs > MAX_STORED_VALUE:
                raise ValidationError("Sale COGS is too large.")
            sale.cogs = cogs
            session.add(
                JournalEntry(
                    owner_id=owner_id,
                    entry_date=sale_date,
                    reference_type="sale_cogs",
                    reference_id=sale.id,
                    debit_account="Cost of Goods Sold",
                    credit_account="Inventory",
                    amount=cogs,
                    memo=f"FIFO COGS for sale of {normalized_quantity} {product.unit} of {product.sku}",
                )
            )
            if revenue is not None:
                session.add(
                    JournalEntry(
                        owner_id=owner_id,
                        entry_date=sale_date,
                        reference_type="sale_revenue",
                        reference_id=sale.id,
                        debit_account="Cash / Accounts Receivable",
                        credit_account="Sales Revenue",
                        amount=revenue,
                        memo=f"Revenue from sale of {normalized_quantity} {product.unit} of {product.sku}",
                    )
                )

            result = SaleResult(
                sale_id=sale.id,
                sku=product.sku,
                quantity=normalized_quantity,
                sold_on=sale_date,
                revenue=revenue,
                cogs=cogs,
                gross_profit=_money(revenue - cogs) if revenue is not None else None,
                layers=tuple(layers),
            )
        return result

    def get_stock(
        self,
        owner_id: int,
        sku: str | None = None,
        language: str | None = None,
    ) -> list[StockLine]:
        normalized_sku = sku.strip().upper() if sku else None
        quantity_sum = func.coalesce(func.sum(PurchaseBatch.remaining_quantity), 0)
        value_sum = func.coalesce(
            func.sum(PurchaseBatch.remaining_quantity * PurchaseBatch.unit_cost), 0
        )
        statement = (
            select(Product.id, Product.sku, Product.name, Product.unit, quantity_sum, value_sum)
            .outerjoin(PurchaseBatch, PurchaseBatch.product_id == Product.id)
            .outerjoin(ArchivedProduct, ArchivedProduct.product_id == Product.id)
            .where(Product.owner_id == owner_id)
            .where(ArchivedProduct.id.is_(None))
            .group_by(Product.id, Product.sku, Product.name, Product.unit)
            .order_by(Product.sku)
        )
        if normalized_sku:
            statement = statement.where(Product.sku == normalized_sku)

        with self._sessions() as session:
            rows = session.execute(statement).all()
            translations: dict[int, dict[str, str]] = {}
            if language and rows:
                translated_rows = session.execute(
                    select(
                        ProductTranslation.product_id,
                        ProductTranslation.language,
                        ProductTranslation.name,
                    ).where(
                        ProductTranslation.product_id.in_([row[0] for row in rows]),
                        ProductTranslation.language == language,
                    )
                ).all()
                for product_id, translation_language, translated_name in translated_rows:
                    translations.setdefault(product_id, {})[translation_language] = translated_name
        if normalized_sku and not rows:
            raise NotFoundError(f"Product {normalized_sku} was not found.")
        return [
            StockLine(
                sku=row[1],
                name=(
                    localize_product_name(row[2], language, translations.get(row[0]))
                    if language
                    else row[2]
                ),
                unit=localize_unit(row[3], language) if language else row[3],
                quantity=Decimal(row[4]),
                inventory_value=_money(Decimal(row[5])),
            )
            for row in rows
        ]

    def archive_product(self, owner_id: int, sku: str) -> ProductResult:
        """Remove a zero-stock product from active inventory without deleting history."""

        normalized_sku = sku.strip().upper()
        with self._sessions.begin() as session:
            product = self._get_product(session, owner_id, normalized_sku)
            already_archived = session.scalar(
                select(ArchivedProduct.id).where(
                    ArchivedProduct.product_id == product.id
                )
            )
            if already_archived:
                raise NotFoundError(f"Product {normalized_sku} is already removed.")
            remaining = session.scalar(
                select(func.coalesce(func.sum(PurchaseBatch.remaining_quantity), 0)).where(
                    PurchaseBatch.product_id == product.id
                )
            )
            remaining_decimal = Decimal(remaining or 0)
            if remaining_decimal > 0:
                raise ValidationError(
                    f"Product {normalized_sku} still has {remaining_decimal} in stock. "
                    "Record the remaining stock correctly before removing it."
                )
            session.add(ArchivedProduct(product_id=product.id, owner_id=owner_id))
            return ProductResult(product.id, product.sku, product.name, product.unit)

    def get_report(
        self,
        owner_id: int,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> InventoryReport:
        if period_start and period_end and period_start > period_end:
            raise ValidationError("Report start date cannot be after the end date.")

        filters = [Product.owner_id == owner_id]
        if period_start:
            filters.append(Sale.sold_on >= period_start)
        if period_end:
            filters.append(Sale.sold_on <= period_end)

        unpriced_count = func.sum(case((Sale.revenue.is_(None), 1), else_=0))
        priced_cogs = func.sum(case((Sale.revenue.is_not(None), Sale.cogs), else_=0))
        statement = (
            select(
                func.count(Sale.id),
                func.coalesce(unpriced_count, 0),
                func.coalesce(func.sum(Sale.quantity), 0),
                func.coalesce(func.sum(Sale.revenue), 0),
                func.coalesce(func.sum(Sale.cogs), 0),
                func.coalesce(priced_cogs, 0),
            )
            .join(Product, Product.id == Sale.product_id)
            .where(*filters)
        )
        with self._sessions() as session:
            row = session.execute(statement).one()

        stock = self.get_stock(owner_id)
        inventory_units = sum((line.quantity for line in stock), start=Decimal("0"))
        inventory_value = sum(
            (line.inventory_value for line in stock), start=Decimal("0")
        )
        revenue = _money(Decimal(row[3]))
        total_cogs = _money(Decimal(row[4]))
        priced_cogs_value = _money(Decimal(row[5]))
        return InventoryReport(
            period_start=period_start,
            period_end=period_end,
            sales_count=int(row[0]),
            unpriced_sales_count=int(row[1]),
            units_sold=Decimal(row[2]),
            revenue=revenue,
            cogs=total_cogs,
            priced_cogs=priced_cogs_value,
            gross_profit=_money(revenue - priced_cogs_value),
            inventory_units=inventory_units,
            inventory_value=_money(inventory_value),
        )

    def get_recent_activity(
        self, owner_id: int, limit: int = 10
    ) -> list[ActivityLine]:
        safe_limit = max(1, min(limit, 25))
        with self._sessions() as session:
            purchases = session.execute(
                select(PurchaseBatch, Product.sku)
                .join(Product, Product.id == PurchaseBatch.product_id)
                .where(Product.owner_id == owner_id)
                .order_by(PurchaseBatch.created_at.desc(), PurchaseBatch.id.desc())
                .limit(safe_limit)
            ).all()
            sales = session.execute(
                select(Sale, Product.sku)
                .join(Product, Product.id == Sale.product_id)
                .where(Product.owner_id == owner_id)
                .order_by(Sale.created_at.desc(), Sale.id.desc())
                .limit(safe_limit)
            ).all()

        activity = [
            ActivityLine(
                kind="purchase",
                reference_id=batch.id,
                occurred_on=batch.purchased_on,
                created_at=batch.created_at,
                sku=sku,
                quantity=batch.original_quantity,
                amount=_money(batch.original_quantity * batch.unit_cost),
                cogs=None,
            )
            for batch, sku in purchases
        ]
        activity.extend(
            ActivityLine(
                kind="sale",
                reference_id=sale.id,
                occurred_on=sale.sold_on,
                created_at=sale.created_at,
                sku=sku,
                quantity=sale.quantity,
                amount=sale.revenue,
                cogs=sale.cogs,
            )
            for sale, sku in sales
        )
        return sorted(
            activity,
            key=lambda item: (item.created_at, item.reference_id),
            reverse=True,
        )[:safe_limit]

    def get_last_purchase_unit_cost(self, owner_id: int, sku: str) -> Decimal | None:
        normalized_sku = sku.strip().upper()
        statement = (
            select(PurchaseBatch.unit_cost)
            .join(Product, Product.id == PurchaseBatch.product_id)
            .where(Product.owner_id == owner_id, Product.sku == normalized_sku)
            .order_by(PurchaseBatch.purchased_on.desc(), PurchaseBatch.id.desc())
            .limit(1)
        )
        with self._sessions() as session:
            value = session.scalar(statement)
        return Decimal(value) if value is not None else None

    def get_last_sale_unit_price(self, owner_id: int, sku: str) -> Decimal | None:
        normalized_sku = sku.strip().upper()
        statement = (
            select(Sale.revenue, Sale.quantity)
            .join(Product, Product.id == Sale.product_id)
            .where(
                Product.owner_id == owner_id,
                Product.sku == normalized_sku,
                Sale.revenue.is_not(None),
            )
            .order_by(Sale.sold_on.desc(), Sale.id.desc())
            .limit(1)
        )
        with self._sessions() as session:
            row = session.execute(statement).one_or_none()
        if row is None:
            return None
        return _money(Decimal(row[0]) / Decimal(row[1]))

    @staticmethod
    def _get_product(session: object, owner_id: int, sku: str) -> Product:
        product = session.scalar(  # type: ignore[attr-defined]
            select(Product)
            .outerjoin(ArchivedProduct, ArchivedProduct.product_id == Product.id)
            .where(
                Product.owner_id == owner_id,
                Product.sku == sku,
                ArchivedProduct.id.is_(None),
            )
        )
        if product is None:
            raise NotFoundError(
                f"Product {sku} was not found. Add it first with the Add product button."
            )
        return product

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from fifo_accounting_bot.schemas import ActivityLine, InventoryReport, SaleResult, StockLine


PHRASES = {
    "en": {
        "no_products": "No products yet. Tap ➕ Add product to create one.", "inventory": "📦 CURRENT FIFO INVENTORY", "total_value": "Total inventory value", "report": "📊 ACCOUNTING REPORT", "all_time": "all time", "sales": "Sales", "units_sold": "Units sold", "revenue": "Recorded revenue", "cogs": "FIFO COGS", "profit": "Gross profit on priced sales", "snapshot": "📦 CURRENT INVENTORY", "on_hand": "Units on hand", "fifo_value": "FIFO inventory value", "dashboard": "🏠 FIFO ACCOUNTER", "products": "Products", "in_stock": "in stock", "performance": "📈 ALL-TIME PERFORMANCE", "activity": "🧾 RECENT ACTIVITY", "no_activity": "🧾 No activity yet. Purchases and sales will appear here.", "purchase": "Purchase", "sale": "Sale", "cost": "cost", "not_supplied": "not supplied",
    },
    "uz": {
        "no_products": "Mahsulotlar yo‘q. ➕ Mahsulot qo‘shish tugmasini bosing.", "inventory": "📦 JORIY FIFO OMBOR", "total_value": "Omborning jami qiymati", "report": "📊 HISOBOT", "all_time": "barcha vaqt", "sales": "Sotuvlar", "units_sold": "Sotilgan birliklar", "revenue": "Kiritilgan daromad", "cogs": "FIFO tannarx", "profit": "Narxli sotuvlar yalpi foydasi", "snapshot": "📦 JORIY OMBOR", "on_hand": "Mavjud birliklar", "fifo_value": "FIFO ombor qiymati", "dashboard": "🏠 FIFO ACCOUNTER", "products": "Mahsulotlar", "in_stock": "omborda", "performance": "📈 UMUMIY NATIJA", "activity": "🧾 SO‘NGGI HARAKATLAR", "no_activity": "🧾 Hali harakat yo‘q. Xarid va sotuvlar shu yerda ko‘rinadi.", "purchase": "Xarid", "sale": "Sotuv", "cost": "qiymat", "not_supplied": "kiritilmagan",
    },
    "tr": {
        "no_products": "Henüz ürün yok. ➕ Ürün ekle düğmesine dokunun.", "inventory": "📦 GÜNCEL FIFO STOK", "total_value": "Toplam stok değeri", "report": "📊 MUHASEBE RAPORU", "all_time": "tüm zamanlar", "sales": "Satışlar", "units_sold": "Satılan birim", "revenue": "Kaydedilen gelir", "cogs": "FIFO satılan mal maliyeti", "profit": "Fiyatlı satışlarda brüt kâr", "snapshot": "📦 GÜNCEL STOK", "on_hand": "Eldeki birim", "fifo_value": "FIFO stok değeri", "dashboard": "🏠 FIFO ACCOUNTER", "products": "Ürünler", "in_stock": "stokta", "performance": "📈 TÜM ZAMANLAR", "activity": "🧾 SON İŞLEMLER", "no_activity": "🧾 Henüz işlem yok. Alış ve satışlar burada görünür.", "purchase": "Alış", "sale": "Satış", "cost": "maliyet", "not_supplied": "girilmedi",
    },
    "it": {
        "no_products": "Nessun prodotto. Tocca ➕ Aggiungi prodotto.", "inventory": "📦 MAGAZZINO FIFO ATTUALE", "total_value": "Valore totale magazzino", "report": "📊 REPORT CONTABILE", "all_time": "tutto il periodo", "sales": "Vendite", "units_sold": "Unità vendute", "revenue": "Ricavi registrati", "cogs": "Costo FIFO", "profit": "Utile lordo sulle vendite con prezzo", "snapshot": "📦 MAGAZZINO ATTUALE", "on_hand": "Unità disponibili", "fifo_value": "Valore magazzino FIFO", "dashboard": "🏠 FIFO ACCOUNTER", "products": "Prodotti", "in_stock": "disponibili", "performance": "📈 RISULTATI COMPLESSIVI", "activity": "🧾 ATTIVITÀ RECENTE", "no_activity": "🧾 Nessuna attività. Acquisti e vendite appariranno qui.", "purchase": "Acquisto", "sale": "Vendita", "cost": "costo", "not_supplied": "non indicato",
    },
    "ru": {
        "no_products": "Товаров пока нет. Нажмите ➕ Добавить товар.", "inventory": "📦 ТЕКУЩИЙ СКЛАД FIFO", "total_value": "Общая стоимость запасов", "report": "📊 БУХГАЛТЕРСКИЙ ОТЧЁТ", "all_time": "за всё время", "sales": "Продажи", "units_sold": "Продано единиц", "revenue": "Учтённая выручка", "cogs": "Себестоимость FIFO", "profit": "Валовая прибыль по продажам с ценой", "snapshot": "📦 ТЕКУЩИЙ СКЛАД", "on_hand": "Единиц в наличии", "fifo_value": "Стоимость запасов FIFO", "dashboard": "🏠 FIFO ACCOUNTER", "products": "Товары", "in_stock": "в наличии", "performance": "📈 РЕЗУЛЬТАТ ЗА ВСЁ ВРЕМЯ", "activity": "🧾 ПОСЛЕДНИЕ ОПЕРАЦИИ", "no_activity": "🧾 Операций пока нет. Покупки и продажи появятся здесь.", "purchase": "Покупка", "sale": "Продажа", "cost": "стоимость", "not_supplied": "не указано",
    },
}

PHRASES["en"].update({"sale_recorded": "Sale #{sale_id} recorded for {sku}", "quantity": "Quantity", "fifo_layers": "FIFO layers", "batch": "Batch", "gross_profit": "Gross profit", "period_to": "to", "unpriced_note": "Note: {count} sale(s) had no sale price; gross profit excludes those sales and their COGS.", "out_of_stock": "Out of stock", "all_stocked": "All listed products currently have stock.", "start_product": "Start by adding your first product."})
PHRASES["uz"].update({"sale_recorded": "{sku} uchun #{sale_id} sotuv yozildi", "quantity": "Miqdor", "fifo_layers": "FIFO qatlamlari", "batch": "Partiya", "gross_profit": "Yalpi foyda", "period_to": "dan", "unpriced_note": "Izoh: {count} ta sotuvda narx ko‘rsatilmagan; yalpi foydaga bu sotuvlar va ularning tannarxi kiritilmadi.", "out_of_stock": "Omborda yo‘q", "all_stocked": "Ro‘yxatdagi barcha mahsulotlar omborda mavjud.", "start_product": "Birinchi mahsulotingizni qo‘shishdan boshlang."})
PHRASES["tr"].update({"sale_recorded": "{sku} için #{sale_id} satış kaydedildi", "quantity": "Miktar", "fifo_layers": "FIFO katmanları", "batch": "Parti", "gross_profit": "Brüt kâr", "period_to": "–", "unpriced_note": "Not: {count} satışta fiyat yoktu; bu satışlar ve maliyetleri brüt kâra dahil edilmedi.", "out_of_stock": "Stokta yok", "all_stocked": "Listelenen tüm ürünler stokta.", "start_product": "İlk ürününüzü ekleyerek başlayın."})
PHRASES["it"].update({"sale_recorded": "Vendita #{sale_id} registrata per {sku}", "quantity": "Quantità", "fifo_layers": "Lotti FIFO", "batch": "Lotto", "gross_profit": "Utile lordo", "period_to": "–", "unpriced_note": "Nota: {count} vendite erano senza prezzo; tali vendite e il relativo costo sono esclusi dall’utile lordo.", "out_of_stock": "Esauriti", "all_stocked": "Tutti i prodotti elencati sono disponibili.", "start_product": "Inizia aggiungendo il primo prodotto."})
PHRASES["ru"].update({"sale_recorded": "Продажа №{sale_id} для {sku} записана", "quantity": "Количество", "fifo_layers": "Слои FIFO", "batch": "Партия", "gross_profit": "Валовая прибыль", "period_to": "—", "unpriced_note": "Примечание: у продаж без цены ({count}) выручка и их себестоимость не включены в валовую прибыль.", "out_of_stock": "Нет в наличии", "all_stocked": "Все товары из списка есть в наличии.", "start_product": "Начните с добавления первого товара."})


def _p(language: str, key: str) -> str:
    return PHRASES.get(language, PHRASES["en"])[key]


def quantity(value: Decimal) -> str:
    rendered = f"{value:,.4f}".rstrip("0").rstrip(".")
    return rendered if rendered != "-0" else "0"


def money(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{rounded:,.2f}"


def format_sale(result: SaleResult, language: str = "en") -> str:
    lines = [
        _p(language, "sale_recorded").format(sale_id=result.sale_id, sku=result.sku),
        f"{_p(language, 'quantity')}: {quantity(result.quantity)}",
        f"{_p(language, 'cogs')}: {money(result.cogs)}",
    ]
    if result.revenue is not None:
        lines.extend(
            [
                f"{_p(language, 'revenue')}: {money(result.revenue)}",
                f"{_p(language, 'gross_profit')}: {money(result.gross_profit or Decimal('0'))}",
            ]
        )
    else:
        lines.append(f"{_p(language, 'revenue')}: {_p(language, 'not_supplied')}")
    lines.append(f"{_p(language, 'fifo_layers')}:")
    lines.extend(
        f"• {_p(language, 'batch')} #{layer.batch_id} ({layer.purchased_on.isoformat()}): "
        f"{quantity(layer.quantity)} × {money(layer.unit_cost)} = {money(layer.cost)}"
        for layer in result.layers
    )
    return "\n".join(lines)


def format_stock(lines: list[StockLine], language: str = "en") -> str:
    if not lines:
        return _p(language, "no_products")
    output = [_p(language, "inventory"), ""]
    for line in lines:
        output.append(
            f"• {line.sku} — {line.name}\n"
            f"  {quantity(line.quantity)} {line.unit}  ·  {money(line.inventory_value)}"
        )
    total_value = sum((line.inventory_value for line in lines), start=Decimal("0"))
    output.extend(["", f"💰 {_p(language, 'total_value')}: {money(total_value)}"])
    return "\n".join(output)


def format_report(report: InventoryReport, language: str = "en") -> str:
    if report.period_start and report.period_end:
        period = f"{report.period_start.isoformat()} {_p(language, 'period_to')} {report.period_end.isoformat()}"
    else:
        period = _p(language, "all_time")
    output = [
        _p(language, "report"),
        f"🗓 {period}",
        "",
        f"• {_p(language, 'sales')}: {report.sales_count}",
        f"• {_p(language, 'units_sold')}: {quantity(report.units_sold)}",
        f"• {_p(language, 'revenue')}: {money(report.revenue)}",
        f"• {_p(language, 'cogs')}: {money(report.cogs)}",
        f"• {_p(language, 'profit')}: {money(report.gross_profit)}",
        "",
        _p(language, "snapshot"),
        f"• {_p(language, 'on_hand')}: {quantity(report.inventory_units)}",
        f"• {_p(language, 'fifo_value')}: {money(report.inventory_value)}",
    ]
    if report.unpriced_sales_count:
        output.append(_p(language, "unpriced_note").format(count=report.unpriced_sales_count))
    return "\n".join(output)


def format_dashboard(stock: list[StockLine], report: InventoryReport, language: str = "en") -> str:
    out_of_stock = [line.sku for line in stock if line.quantity <= 0]
    stocked_products = len(stock) - len(out_of_stock)
    output = [
        _p(language, "dashboard"),
        "",
        _p(language, "snapshot"),
        f"• {_p(language, 'products')}: {len(stock)} ({stocked_products} {_p(language, 'in_stock')})",
        f"• {_p(language, 'on_hand')}: {quantity(report.inventory_units)}",
        f"• {_p(language, 'fifo_value')}: {money(report.inventory_value)}",
        "",
        _p(language, "performance"),
        f"• {_p(language, 'sales')}: {report.sales_count}",
        f"• {_p(language, 'revenue')}: {money(report.revenue)}",
        f"• {_p(language, 'cogs')}: {money(report.cogs)}",
        f"• {_p(language, 'profit')}: {money(report.gross_profit)}",
    ]
    if out_of_stock:
        shown = ", ".join(out_of_stock[:5])
        suffix = "…" if len(out_of_stock) > 5 else ""
        output.extend(["", f"⚠️ {_p(language, 'out_of_stock')}: {shown}{suffix}"])
    elif stock:
        output.extend(["", f"✅ {_p(language, 'all_stocked')}"])
    else:
        output.extend(["", _p(language, "start_product")])
    return "\n".join(output)


def format_activity(activity: list[ActivityLine], language: str = "en") -> str:
    if not activity:
        return _p(language, "no_activity")
    output = [_p(language, "activity"), ""]
    for item in activity:
        if item.kind == "purchase":
            output.append(
                f"📥 {_p(language, 'purchase')} · {item.occurred_on.isoformat()} · {item.sku}\n"
                f"   #{item.reference_id} · {quantity(item.quantity)} · {_p(language, 'cost')} {money(item.amount or Decimal('0'))}"
            )
        else:
            revenue = (
                money(item.amount) if item.amount is not None else _p(language, "not_supplied")
            )
            output.append(
                f"📤 {_p(language, 'sale')} · {item.occurred_on.isoformat()} · {item.sku}\n"
                f"   #{item.reference_id} · {quantity(item.quantity)} · {_p(language, 'revenue')} {revenue} · {_p(language, 'cogs')} {money(item.cogs or Decimal('0'))}"
            )
    return "\n".join(output)

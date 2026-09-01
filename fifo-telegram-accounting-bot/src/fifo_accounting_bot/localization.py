from __future__ import annotations

"""Language-neutral catalog helpers.

Accounting records keep stable SKUs and numeric values.  Product labels and units
are presentation data, so they can be shown in the user's selected language
without rewriting FIFO batches, sales, or journal entries.
"""

from collections.abc import Mapping

SUPPORTED_LANGUAGES = ("uz", "tr", "it", "en", "ru")


PRODUCT_GLOSSARY: dict[str, dict[str, str]] = {
    "pencil": {"en": "Pencil", "uz": "Qalam", "tr": "Kurşun kalem", "it": "Matita", "ru": "Карандаш"},
    "pen": {"en": "Pen", "uz": "Ruchka", "tr": "Tükenmez kalem", "it": "Penna", "ru": "Ручка"},
    "notebook": {"en": "Notebook", "uz": "Daftar", "tr": "Defter", "it": "Quaderno", "ru": "Тетрадь"},
    "paper": {"en": "Paper", "uz": "Qog‘oz", "tr": "Kağıt", "it": "Carta", "ru": "Бумага"},
    "printer paper": {"en": "Printer paper", "uz": "Printer qog‘ozi", "tr": "Yazıcı kağıdı", "it": "Carta per stampante", "ru": "Бумага для принтера"},
    "coffee": {"en": "Coffee", "uz": "Qahva", "tr": "Kahve", "it": "Caffè", "ru": "Кофе"},
    "coffee beans": {"en": "Coffee beans", "uz": "Qahva donalari", "tr": "Kahve çekirdekleri", "it": "Chicchi di caffè", "ru": "Кофейные зёрна"},
    "tea": {"en": "Tea", "uz": "Choy", "tr": "Çay", "it": "Tè", "ru": "Чай"},
    "sugar": {"en": "Sugar", "uz": "Shakar", "tr": "Şeker", "it": "Zucchero", "ru": "Сахар"},
    "milk": {"en": "Milk", "uz": "Sut", "tr": "Süt", "it": "Latte", "ru": "Молоко"},
    "water": {"en": "Water", "uz": "Suv", "tr": "Su", "it": "Acqua", "ru": "Вода"},
    "bread": {"en": "Bread", "uz": "Non", "tr": "Ekmek", "it": "Pane", "ru": "Хлеб"},
    "rice": {"en": "Rice", "uz": "Guruch", "tr": "Pirinç", "it": "Riso", "ru": "Рис"},
    "flour": {"en": "Flour", "uz": "Un", "tr": "Un", "it": "Farina", "ru": "Мука"},
    "cooking oil": {"en": "Cooking oil", "uz": "O‘simlik yog‘i", "tr": "Yemeklik yağ", "it": "Olio da cucina", "ru": "Растительное масло"},
    "soap": {"en": "Soap", "uz": "Sovun", "tr": "Sabun", "it": "Sapone", "ru": "Мыло"},
    "shirt": {"en": "Shirt", "uz": "Ko‘ylak", "tr": "Gömlek", "it": "Camicia", "ru": "Рубашка"},
    "shoes": {"en": "Shoes", "uz": "Poyabzal", "tr": "Ayakkabı", "it": "Scarpe", "ru": "Обувь"},
    "phone": {"en": "Phone", "uz": "Telefon", "tr": "Telefon", "it": "Telefono", "ru": "Телефон"},
    "laptop": {"en": "Laptop", "uz": "Noutbuk", "tr": "Dizüstü bilgisayar", "it": "Portatile", "ru": "Ноутбук"},
    "box": {"en": "Box", "uz": "Quti", "tr": "Kutu", "it": "Scatola", "ru": "Коробка"},
}

UNIT_LABELS: dict[str, dict[str, str]] = {
    "pcs": {"en": "pcs", "uz": "dona", "tr": "adet", "it": "pz", "ru": "шт"},
    "kg": {"en": "kg", "uz": "kg", "tr": "kg", "it": "kg", "ru": "кг"},
    "g": {"en": "g", "uz": "g", "tr": "g", "it": "g", "ru": "г"},
    "l": {"en": "l", "uz": "l", "tr": "l", "it": "l", "ru": "л"},
    "ml": {"en": "ml", "uz": "ml", "tr": "ml", "it": "ml", "ru": "мл"},
    "box": {"en": "box", "uz": "quti", "tr": "kutu", "it": "scatola", "ru": "коробка"},
    "pack": {"en": "pack", "uz": "to‘plam", "tr": "paket", "it": "confezione", "ru": "упаковка"},
    "m": {"en": "m", "uz": "m", "tr": "m", "it": "m", "ru": "м"},
}

ACCOUNT_LABELS: dict[str, dict[str, str]] = {
    "1000": {"en": "Cash", "uz": "Kassa", "tr": "Kasa", "it": "Cassa", "ru": "Касса"},
    "1010": {"en": "Bank", "uz": "Bank", "tr": "Banka", "it": "Banca", "ru": "Банк"},
    "1100": {"en": "Accounts Receivable", "uz": "Debitorlik qarzi", "tr": "Ticari alacaklar", "it": "Crediti clienti", "ru": "Дебиторская задолженность"},
    "1200": {"en": "Inventory", "uz": "Ombor zaxirasi", "tr": "Stok", "it": "Magazzino", "ru": "Запасы"},
    "1300": {"en": "Tax Receivable", "uz": "Soliq bo‘yicha talab", "tr": "Vergi alacağı", "it": "Credito d’imposta", "ru": "Налог к возмещению"},
    "1500": {"en": "Equipment", "uz": "Uskunalar", "tr": "Ekipman", "it": "Attrezzature", "ru": "Оборудование"},
    "1590": {"en": "Accumulated Depreciation", "uz": "Jamg‘arilgan amortizatsiya", "tr": "Birikmiş amortisman", "it": "Fondo ammortamento", "ru": "Накопленная амортизация"},
    "2000": {"en": "Accounts Payable", "uz": "Kreditorlik qarzi", "tr": "Ticari borçlar", "it": "Debiti fornitori", "ru": "Кредиторская задолженность"},
    "2100": {"en": "Tax Payable", "uz": "Soliq majburiyati", "tr": "Vergi borcu", "it": "Debiti tributari", "ru": "Налог к уплате"},
    "2200": {"en": "Loans Payable", "uz": "Kreditlar", "tr": "Kredi borçları", "it": "Finanziamenti passivi", "ru": "Займы к погашению"},
    "3000": {"en": "Owner's Equity", "uz": "Egasi kapitali", "tr": "Öz sermaye", "it": "Patrimonio netto", "ru": "Капитал владельца"},
    "4000": {"en": "Product Sales", "uz": "Mahsulot savdosi", "tr": "Ürün satışları", "it": "Vendite prodotti", "ru": "Продажа товаров"},
    "4100": {"en": "Service Revenue", "uz": "Xizmat daromadi", "tr": "Hizmet geliri", "it": "Ricavi da servizi", "ru": "Выручка от услуг"},
    "4200": {"en": "Other Income", "uz": "Boshqa daromad", "tr": "Diğer gelir", "it": "Altri ricavi", "ru": "Прочие доходы"},
    "5000": {"en": "Cost of Goods Sold", "uz": "Sotilgan mahsulot tannarxi", "tr": "Satılan malın maliyeti", "it": "Costo del venduto", "ru": "Себестоимость продаж"},
    "6000": {"en": "Rent Expense", "uz": "Ijara xarajati", "tr": "Kira gideri", "it": "Costo affitto", "ru": "Расходы на аренду"},
    "6010": {"en": "Utilities Expense", "uz": "Kommunal xarajat", "tr": "Fatura giderleri", "it": "Utenze", "ru": "Коммунальные расходы"},
    "6020": {"en": "Wages Expense", "uz": "Ish haqi xarajati", "tr": "Ücret giderleri", "it": "Costo del personale", "ru": "Расходы на оплату труда"},
    "6030": {"en": "Marketing Expense", "uz": "Marketing xarajati", "tr": "Pazarlama gideri", "it": "Costi marketing", "ru": "Расходы на маркетинг"},
    "6040": {"en": "Travel Expense", "uz": "Safar xarajati", "tr": "Seyahat gideri", "it": "Spese di trasferta", "ru": "Командировочные расходы"},
    "6050": {"en": "Office Supplies Expense", "uz": "Ofis buyumlari xarajati", "tr": "Ofis malzemesi gideri", "it": "Materiale d’ufficio", "ru": "Офисные расходы"},
    "6060": {"en": "Bank Fees Expense", "uz": "Bank komissiyasi", "tr": "Banka masrafları", "it": "Commissioni bancarie", "ru": "Банковские комиссии"},
    "6070": {"en": "Depreciation Expense", "uz": "Amortizatsiya xarajati", "tr": "Amortisman gideri", "it": "Ammortamenti", "ru": "Расходы на амортизацию"},
    "6990": {"en": "Other Operating Expense", "uz": "Boshqa operatsion xarajat", "tr": "Diğer faaliyet gideri", "it": "Altri costi operativi", "ru": "Прочие операционные расходы"},
}


def _normal(value: str) -> str:
    return " ".join(value.strip().casefold().split())


_PRODUCT_INDEX = {
    _normal(label): concept
    for concept, labels in PRODUCT_GLOSSARY.items()
    for label in labels.values()
}

_UNIT_INDEX = {
    _normal(label): canonical
    for canonical, labels in UNIT_LABELS.items()
    for label in labels.values()
}
_UNIT_INDEX.update(
    {
        "piece": "pcs", "pieces": "pcs", "unit": "pcs", "units": "pcs",
        "dona": "pcs", "adet": "pcs", "pezzo": "pcs", "pezzi": "pcs", "штука": "pcs",
        "kilogram": "kg", "kilograms": "kg", "килограмм": "kg",
        "liter": "l", "litre": "l", "liters": "l", "litres": "l", "литр": "l",
        "package": "pack", "packet": "pack", "пачка": "pack",
    }
)


def product_translations(name: str) -> dict[str, str]:
    """Return known translations for a catalog label, or an empty mapping."""

    concept = _PRODUCT_INDEX.get(_normal(name))
    return dict(PRODUCT_GLOSSARY[concept]) if concept else {}


def localize_product_name(
    original: str,
    language: str,
    stored: Mapping[str, str] | None = None,
) -> str:
    if stored and stored.get(language):
        return stored[language]
    translations = product_translations(original)
    return translations.get(language, original)


def canonicalize_unit(unit: str) -> str:
    normalized = _normal(unit)
    return _UNIT_INDEX.get(normalized, normalized)


def localize_unit(unit: str, language: str) -> str:
    canonical = canonicalize_unit(unit)
    labels = UNIT_LABELS.get(canonical)
    return labels.get(language, labels["en"]) if labels else unit


def localize_account_name(code: str, original: str, language: str) -> str:
    labels = ACCOUNT_LABELS.get(code)
    return labels.get(language, original) if labels else original

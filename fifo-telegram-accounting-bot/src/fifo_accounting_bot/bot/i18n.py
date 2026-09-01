from __future__ import annotations

LANGUAGES = ("uz", "tr", "it", "en", "ru")
DEFAULT_LANGUAGE = "en"

LANGUAGE_BUTTONS = {
    "🇺🇿 O‘zbekcha": "uz",
    "🇹🇷 Türkçe": "tr",
    "🇮🇹 Italiano": "it",
    "🇬🇧 English": "en",
    "🇷🇺 Русский": "ru",
}

LANGUAGE_DISPLAY = {
    "uz": "O‘zbekcha",
    "tr": "Türkçe",
    "it": "Italiano",
    "en": "English",
    "ru": "Русский",
}

FIELD_NAMES = {
    "quantity": {"en": "Quantity", "uz": "Miqdor", "tr": "Miktar", "it": "Quantità", "ru": "Количество"},
    "unit_cost": {"en": "Unit cost", "uz": "Birlik tannarxi", "tr": "Birim maliyeti", "it": "Costo unitario", "ru": "Цена за единицу"},
    "sale_price": {"en": "Sale price", "uz": "Sotuv narxi", "tr": "Satış fiyatı", "it": "Prezzo di vendita", "ru": "Цена продажи"},
}

BUTTONS: dict[str, dict[str, str]] = {
    "dashboard": {"en": "🏠 Dashboard", "uz": "🏠 Bosh sahifa", "tr": "🏠 Gösterge", "it": "🏠 Panoramica", "ru": "🏠 Главная"},
    "add_product": {"en": "➕ Add product", "uz": "➕ Mahsulot qo‘shish", "tr": "➕ Ürün ekle", "it": "➕ Aggiungi prodotto", "ru": "➕ Добавить товар"},
    "purchase": {"en": "📥 Purchase", "uz": "📥 Xarid", "tr": "📥 Alış", "it": "📥 Acquisto", "ru": "📥 Покупка"},
    "sale": {"en": "📤 Sale", "uz": "📤 Sotuv", "tr": "📤 Satış", "it": "📤 Vendita", "ru": "📤 Продажа"},
    "inventory": {"en": "📦 Inventory", "uz": "📦 Ombor", "tr": "📦 Stok", "it": "📦 Magazzino", "ru": "📦 Склад"},
    "activity": {"en": "🧾 Activity", "uz": "🧾 Harakatlar", "tr": "🧾 İşlemler", "it": "🧾 Attività", "ru": "🧾 Операции"},
    "report": {"en": "📊 Reports", "uz": "📊 Hisobotlar", "tr": "📊 Raporlar", "it": "📊 Report", "ru": "📊 Отчёты"},
    "smart_import": {"en": "📷 QR / Smart import", "uz": "📷 QR / Aqlli import", "tr": "📷 QR / Akıllı aktarım", "it": "📷 QR / Import smart", "ru": "📷 QR / Умный импорт"},
    "help_ai": {"en": "🧠 Help & AI", "uz": "🧠 Yordam va AI", "tr": "🧠 Yardım ve AI", "it": "🧠 Aiuto e IA", "ru": "🧠 Помощь и ИИ"},
    "settings": {"en": "⚙️ Settings", "uz": "⚙️ Sozlamalar", "tr": "⚙️ Ayarlar", "it": "⚙️ Impostazioni", "ru": "⚙️ Настройки"},
    "language": {"en": "🌐 Change language", "uz": "🌐 Tilni o‘zgartirish", "tr": "🌐 Dili değiştir", "it": "🌐 Cambia lingua", "ru": "🌐 Сменить язык"},
    "cancel": {"en": "❌ Cancel", "uz": "❌ Bekor qilish", "tr": "❌ İptal", "it": "❌ Annulla", "ru": "❌ Отмена"},
    "today": {"en": "📅 Today", "uz": "📅 Bugun", "tr": "📅 Bugün", "it": "📅 Oggi", "ru": "📅 Сегодня"},
    "skip_price": {"en": "Skip sale price", "uz": "Sotuv narxini o‘tkazib yuborish", "tr": "Satış fiyatını atla", "it": "Salta prezzo di vendita", "ru": "Пропустить цену продажи"},
    "all_time": {"en": "All time", "uz": "Barcha vaqt", "tr": "Tüm zamanlar", "it": "Tutto il periodo", "ru": "За всё время"},
    "today_report": {"en": "Today", "uz": "Bugun", "tr": "Bugün", "it": "Oggi", "ru": "Сегодня"},
    "this_month": {"en": "This month", "uz": "Shu oy", "tr": "Bu ay", "it": "Questo mese", "ru": "Этот месяц"},
    "last_30": {"en": "Last 30 days", "uz": "Oxirgi 30 kun", "tr": "Son 30 gün", "it": "Ultimi 30 giorni", "ru": "Последние 30 дней"},
    "custom_range": {"en": "Custom date range", "uz": "Sana oralig‘i", "tr": "Özel tarih aralığı", "it": "Intervallo personalizzato", "ru": "Свой период"},
    "main_menu": {"en": "⬅️ Main menu", "uz": "⬅️ Asosiy menyu", "tr": "⬅️ Ana menü", "it": "⬅️ Menu principale", "ru": "⬅️ Главное меню"},
    "type_sku": {"en": "⌨️ Type SKU", "uz": "⌨️ SKU yozish", "tr": "⌨️ SKU yaz", "it": "⌨️ Inserisci SKU", "ru": "⌨️ Ввести SKU"},
    "confirm": {"en": "✅ Confirm", "uz": "✅ Tasdiqlash", "tr": "✅ Onayla", "it": "✅ Conferma", "ru": "✅ Подтвердить"},
    "start_over": {"en": "↩️ Start over", "uz": "↩️ Qayta boshlash", "tr": "↩️ Baştan başla", "it": "↩️ Ricomincia", "ru": "↩️ Начать заново"},
    "buy_scanned": {"en": "📥 Purchase scanned item", "uz": "📥 Skanerlanganini xarid qilish", "tr": "📥 Taranan ürünü al", "it": "📥 Acquista articolo letto", "ru": "📥 Купить сканированный товар"},
    "sell_scanned": {"en": "📤 Sell scanned item", "uz": "📤 Skanerlanganini sotish", "tr": "📤 Taranan ürünü sat", "it": "📤 Vendi articolo letto", "ru": "📤 Продать сканированный товар"},
    "view_stock": {"en": "📋 View stock", "uz": "📋 Qoldiqni ko‘rish", "tr": "📋 Stoku görüntüle", "it": "📋 Vedi scorte", "ru": "📋 Посмотреть остатки"},
    "remove_product": {"en": "🗑 Remove product", "uz": "🗑 Mahsulotni olib tashlash", "tr": "🗑 Ürünü kaldır", "it": "🗑 Rimuovi prodotto", "ru": "🗑 Удалить товар"},
    "ask_ai": {"en": "✨ Ask AI", "uz": "✨ AI’dan so‘rash", "tr": "✨ AI'ya sor", "it": "✨ Chiedi all’IA", "ru": "✨ Спросить ИИ"},
    "explain_report": {"en": "💡 Explain my report", "uz": "💡 Hisobotimni tushuntirish", "tr": "💡 Raporumu açıkla", "it": "💡 Spiega il mio report", "ru": "💡 Объяснить мой отчёт"},
    "guide": {"en": "📘 How the bot works", "uz": "📘 Bot qanday ishlaydi", "tr": "📘 Bot nasıl çalışır", "it": "📘 Come funziona", "ru": "📘 Как работает бот"},
    "legal": {"en": "⚖️ Legal & privacy", "uz": "⚖️ Huquqiy va maxfiylik", "tr": "⚖️ Yasal ve gizlilik", "it": "⚖️ Note legali e privacy", "ru": "⚖️ Правила и конфиденциальность"},
    "about": {"en": "ℹ️ About & version", "uz": "ℹ️ Bot va versiya", "tr": "ℹ️ Hakkında ve sürüm", "it": "ℹ️ Info e versione", "ru": "ℹ️ О боте и версия"},
    "ai_enable": {"en": "✅ Enable AI", "uz": "✅ AI’ni yoqish", "tr": "✅ AI'yı etkinleştir", "it": "✅ Attiva IA", "ru": "✅ Включить ИИ"},
    "ai_disable": {"en": "⏸ Disable AI", "uz": "⏸ AI’ni o‘chirish", "tr": "⏸ AI'yı kapat", "it": "⏸ Disattiva IA", "ru": "⏸ Выключить ИИ"},
    "owner_panel": {"en": "🛡 Owner panel", "uz": "🛡 Egasi paneli", "tr": "🛡 Sahip paneli", "it": "🛡 Pannello proprietario", "ru": "🛡 Панель владельца"},
    "owner_users": {"en": "👥 Users", "uz": "👥 Foydalanuvchilar", "tr": "👥 Kullanıcılar", "it": "👥 Utenti", "ru": "👥 Пользователи"},
    "owner_health": {"en": "🩺 Bot health", "uz": "🩺 Bot holati", "tr": "🩺 Bot sağlığı", "it": "🩺 Stato del bot", "ru": "🩺 Состояние бота"},
    "money_in": {"en": "💰 Sales & income", "uz": "💰 Savdo va daromad", "tr": "💰 Satış ve gelir", "it": "💰 Vendite e ricavi", "ru": "💰 Продажи и доходы"},
    "money_out": {"en": "💸 Bills & expenses", "uz": "💸 Hisoblar va xarajatlar", "tr": "💸 Faturalar ve giderler", "it": "💸 Fatture e spese", "ru": "💸 Счета и расходы"},
    "banking": {"en": "🏦 Cash & banking", "uz": "🏦 Kassa va bank", "tr": "🏦 Kasa ve banka", "it": "🏦 Cassa e banca", "ru": "🏦 Касса и банк"},
    "contacts": {"en": "👥 Customers & suppliers", "uz": "👥 Mijozlar va yetkazuvchilar", "tr": "👥 Müşteriler ve tedarikçiler", "it": "👥 Clienti e fornitori", "ru": "👥 Клиенты и поставщики"},
    "financial_reports": {"en": "📈 Financial reports", "uz": "📈 Moliyaviy hisobotlar", "tr": "📈 Finansal raporlar", "it": "📈 Bilanci e report", "ru": "📈 Финансовые отчёты"},
    "quick_income": {"en": "➕ Record income", "uz": "➕ Daromad yozish", "tr": "➕ Gelir kaydet", "it": "➕ Registra ricavo", "ru": "➕ Записать доход"},
    "customer_invoice": {"en": "🧾 Create invoice", "uz": "🧾 Hisob-faktura yaratish", "tr": "🧾 Fatura oluştur", "it": "🧾 Crea fattura", "ru": "🧾 Создать счёт"},
    "receive_payment": {"en": "💳 Receive payment", "uz": "💳 To‘lovni qabul qilish", "tr": "💳 Tahsilat al", "it": "💳 Incassa pagamento", "ru": "💳 Получить оплату"},
    "quick_expense": {"en": "➖ Record expense", "uz": "➖ Xarajat yozish", "tr": "➖ Gider kaydet", "it": "➖ Registra spesa", "ru": "➖ Записать расход"},
    "supplier_bill": {"en": "📄 Enter supplier bill", "uz": "📄 Yetkazuvchi hisobini kiritish", "tr": "📄 Tedarikçi faturası gir", "it": "📄 Registra fattura fornitore", "ru": "📄 Ввести счёт поставщика"},
    "pay_bill": {"en": "💳 Pay supplier bill", "uz": "💳 Yetkazuvchiga to‘lash", "tr": "💳 Tedarikçi faturası öde", "it": "💳 Paga fornitore", "ru": "💳 Оплатить поставщику"},
    "add_contact": {"en": "➕ Add contact", "uz": "➕ Kontakt qo‘shish", "tr": "➕ Kişi ekle", "it": "➕ Aggiungi contatto", "ru": "➕ Добавить контакт"},
    "list_contacts": {"en": "📇 Contact list", "uz": "📇 Kontaktlar", "tr": "📇 Kişi listesi", "it": "📇 Elenco contatti", "ru": "📇 Список контактов"},
    "cash_balances": {"en": "💵 Cash & bank balances", "uz": "💵 Kassa va bank qoldiqlari", "tr": "💵 Kasa ve banka bakiyeleri", "it": "💵 Saldi cassa e banca", "ru": "💵 Остатки кассы и банка"},
    "transfer": {"en": "🔁 Transfer money", "uz": "🔁 Pul o‘tkazish", "tr": "🔁 Para aktar", "it": "🔁 Trasferisci denaro", "ru": "🔁 Перевести деньги"},
    "manual_journal": {"en": "📚 Manual journal", "uz": "📚 Qo‘lda provodka", "tr": "📚 Manuel yevmiye", "it": "📚 Prima nota manuale", "ru": "📚 Ручная проводка"},
    "correct_transaction": {"en": "↩️ Correct transaction", "uz": "↩️ Tranzaksiyani tuzatish", "tr": "↩️ İşlemi düzelt", "it": "↩️ Correggi movimento", "ru": "↩️ Исправить операцию"},
    "recent_ledger": {"en": "📖 General ledger", "uz": "📖 Bosh kitob", "tr": "📖 Büyük defter", "it": "📖 Libro mastro", "ru": "📖 Главная книга"},
    "profit_loss": {"en": "📊 Profit & loss", "uz": "📊 Foyda va zarar", "tr": "📊 Kâr ve zarar", "it": "📊 Conto economico", "ru": "📊 Прибыли и убытки"},
    "balance_sheet": {"en": "⚖️ Balance sheet", "uz": "⚖️ Balans", "tr": "⚖️ Bilanço", "it": "⚖️ Stato patrimoniale", "ru": "⚖️ Баланс"},
    "trial_balance": {"en": "🧮 Trial balance", "uz": "🧮 Aylanma balansi", "tr": "🧮 Mizan", "it": "🧮 Bilancio di verifica", "ru": "🧮 Оборотно-сальдовая ведомость"},
    "receivables": {"en": "📥 Receivables", "uz": "📥 Debitorlik", "tr": "📥 Alacaklar", "it": "📥 Crediti clienti", "ru": "📥 Дебиторская задолженность"},
    "payables": {"en": "📤 Payables", "uz": "📤 Kreditorlik", "tr": "📤 Borçlar", "it": "📤 Debiti fornitori", "ru": "📤 Кредиторская задолженность"},
    "contact_customer": {"en": "Customer", "uz": "Mijoz", "tr": "Müşteri", "it": "Cliente", "ru": "Клиент"},
    "contact_supplier": {"en": "Supplier", "uz": "Yetkazuvchi", "tr": "Tedarikçi", "it": "Fornitore", "ru": "Поставщик"},
    "contact_both": {"en": "Both", "uz": "Ikkalasi", "tr": "Her ikisi", "it": "Entrambi", "ru": "Оба"},
    "cash_account": {"en": "Cash", "uz": "Kassa", "tr": "Kasa", "it": "Cassa", "ru": "Касса"},
    "bank_account": {"en": "Bank", "uz": "Bank", "tr": "Banka", "it": "Banca", "ru": "Банк"},
    "skip_details": {"en": "Skip", "uz": "O‘tkazib yuborish", "tr": "Atla", "it": "Salta", "ru": "Пропустить"},
    "full_amount": {"en": "Pay full amount", "uz": "To‘liq summani to‘lash", "tr": "Tamamını öde", "it": "Paga tutto", "ru": "Оплатить полностью"},
    "expense_rent": {"en": "Rent", "uz": "Ijara", "tr": "Kira", "it": "Affitto", "ru": "Аренда"},
    "expense_utilities": {"en": "Utilities", "uz": "Kommunal", "tr": "Faturalar", "it": "Utenze", "ru": "Коммунальные"},
    "expense_wages": {"en": "Wages", "uz": "Ish haqi", "tr": "Ücretler", "it": "Stipendi", "ru": "Зарплата"},
    "expense_marketing": {"en": "Marketing", "uz": "Marketing", "tr": "Pazarlama", "it": "Marketing", "ru": "Маркетинг"},
    "expense_travel": {"en": "Travel", "uz": "Safar", "tr": "Seyahat", "it": "Trasferte", "ru": "Поездки"},
    "expense_office": {"en": "Office supplies", "uz": "Ofis buyumlari", "tr": "Ofis malzemeleri", "it": "Materiale ufficio", "ru": "Офисные материалы"},
    "expense_other": {"en": "Other expense", "uz": "Boshqa xarajat", "tr": "Diğer gider", "it": "Altra spesa", "ru": "Другой расход"},
}

TEXT: dict[str, dict[str, str]] = {
    "choose_language": {
        "en": "🌐 Choose your language\n\nYou can change it later in Settings.",
        "uz": "🌐 Tilingizni tanlang\n\nKeyin Sozlamalarda o‘zgartirishingiz mumkin.",
        "tr": "🌐 Dilinizi seçin\n\nDaha sonra Ayarlar'dan değiştirebilirsiniz.",
        "it": "🌐 Scegli la lingua\n\nPotrai cambiarla in seguito nelle Impostazioni.",
        "ru": "🌐 Выберите язык\n\nПозже его можно изменить в Настройках.",
    },
    "welcome": {
        "en": "👋 Welcome to Accounter\n\nYour bookkeeping, invoices, bills, banking, reports, and FIFO inventory are organized below:",
        "uz": "👋 Accounter’ga xush kelibsiz\n\nBuxgalteriya, hisoblar, bank, hisobotlar va FIFO ombori quyida:",
        "tr": "👋 Accounter'a hoş geldiniz\n\nMuhasebe, faturalar, banka, raporlar ve FIFO stok işlemleri aşağıda:",
        "it": "👋 Benvenuto in Accounter\n\nContabilità, fatture, banca, bilanci e magazzino FIFO sono organizzati qui sotto:",
        "ru": "👋 Добро пожаловать в Accounter\n\nУчёт, счета, банк, отчёты и FIFO-склад собраны ниже:",
    },
    "cancelled": {"en": "Cancelled. Choose another action:", "uz": "Bekor qilindi. Boshqa amalni tanlang:", "tr": "İptal edildi. Başka bir işlem seçin:", "it": "Operazione annullata. Scegli un’altra azione:", "ru": "Отменено. Выберите другое действие:"},
    "role_owner": {"en": "Owner", "uz": "Egasi", "tr": "Sahip", "it": "Proprietario", "ru": "Владелец"},
    "role_user": {"en": "User", "uz": "Foydalanuvchi", "tr": "Kullanıcı", "it": "Utente", "ru": "Пользователь"},
    "settings": {
        "en": "⚙️ SETTINGS\n\n👤 Role: {role}\n🌐 Language: {language_name}\n🧠 AI helper: {ai}\n\nAI is contacted only after you explicitly ask it a question.",
        "uz": "⚙️ SOZLAMALAR\n\n👤 Rol: {role}\n🌐 Til: {language_name}\n🧠 AI yordamchi: {ai}\n\nAI faqat siz aniq savol berganingizda ishlaydi.",
        "tr": "⚙️ AYARLAR\n\n👤 Rol: {role}\n🌐 Dil: {language_name}\n🧠 AI yardımcısı: {ai}\n\nAI yalnızca açıkça soru sorduğunuzda çalışır.",
        "it": "⚙️ IMPOSTAZIONI\n\n👤 Ruolo: {role}\n🌐 Lingua: {language_name}\n🧠 Assistente IA: {ai}\n\nL’IA viene contattata solo quando fai esplicitamente una domanda.",
        "ru": "⚙️ НАСТРОЙКИ\n\n👤 Роль: {role}\n🌐 Язык: {language_name}\n🧠 ИИ-помощник: {ai}\n\nИИ вызывается только после вашего явного вопроса.",
    },
    "ai_on": {"en": "enabled", "uz": "yoqilgan", "tr": "açık", "it": "attiva", "ru": "включён"},
    "ai_off": {"en": "disabled", "uz": "o‘chirilgan", "tr": "kapalı", "it": "disattivata", "ru": "выключен"},
    "ai_unavailable": {"en": "not connected by owner", "uz": "egasi tomonidan ulanmagan", "tr": "sahip tarafından bağlanmadı", "it": "non collegata dal proprietario", "ru": "не подключён владельцем"},
    "help_panel": {
        "en": "🧠 HELP & AI\n\nUse the guide for normal help. AI stays silent unless you tap Ask AI or Explain my report.",
        "uz": "🧠 YORDAM VA AI\n\nOddiy yordam uchun qo‘llanmani oching. AI faqat so‘raganingizda javob beradi.",
        "tr": "🧠 YARDIM VE AI\n\nNormal yardım için rehberi kullanın. AI yalnızca siz istediğinizde cevap verir.",
        "it": "🧠 AIUTO E IA\n\nUsa la guida per l’aiuto normale. L’IA risponde soltanto su richiesta.",
        "ru": "🧠 ПОМОЩЬ И ИИ\n\nДля обычной помощи откройте руководство. ИИ отвечает только по запросу.",
    },
    "guide": {
        "en": "📘 HOW IT WORKS\n\n1. Sales & income records receipts and customer invoices.\n2. Bills & expenses records costs, supplier bills, and payments.\n3. Cash & banking shows balances, transfers, journals, and corrections.\n4. Financial reports provide profit & loss, balance sheet, trial balance, receivables, and payables.\n5. Inventory keeps product quantities and automatically calculates FIFO COGS.\n\nEvery accounting entry is double-entry and corrections create an audit-preserving reversal.",
        "uz": "📘 QANDAY ISHLAYDI\n\n1. Savdo va daromad tushumlar hamda mijoz hisoblarini yozadi.\n2. Hisoblar va xarajatlar xarajat, yetkazuvchi hisobi va to‘lovlarni yozadi.\n3. Kassa va bank qoldiq, o‘tkazma, provodka va tuzatishlarni ko‘rsatadi.\n4. Moliyaviy hisobotlar foyda-zarar, balans, qarzdorlik va sinov balansini beradi.\n5. Ombor miqdor va FIFO tannarxini avtomatik hisoblaydi.\n\nHar bir yozuv ikki tomonlama, tuzatish esa tarixni saqlovchi teskari provodkadir.",
        "tr": "📘 NASIL ÇALIŞIR\n\n1. Satış ve gelir tahsilatları ve müşteri faturalarını kaydeder.\n2. Faturalar ve giderler maliyetleri, tedarikçi faturalarını ve ödemeleri kaydeder.\n3. Kasa ve banka bakiyeleri, transferleri, yevmiyeyi ve düzeltmeleri gösterir.\n4. Finansal raporlar kâr-zarar, bilanço, mizan, alacak ve borçları sunar.\n5. Stok miktarı ve FIFO maliyetini otomatik hesaplar.\n\nHer kayıt çift taraflıdır; düzeltmeler geçmişi koruyan ters kayıt oluşturur.",
        "it": "📘 COME FUNZIONA\n\n1. Vendite e ricavi registra incassi e fatture clienti.\n2. Fatture e spese registra costi, fatture fornitori e pagamenti.\n3. Cassa e banca mostra saldi, trasferimenti, prima nota e storni.\n4. I report includono conto economico, stato patrimoniale, bilancio di verifica, crediti e debiti.\n5. Il magazzino calcola automaticamente quantità e costo FIFO.\n\nOgni registrazione è in partita doppia; le correzioni creano uno storno tracciabile.",
        "ru": "📘 КАК ЭТО РАБОТАЕТ\n\n1. Продажи и доходы учитывают поступления и счета клиентам.\n2. Счета и расходы учитывают затраты, счета поставщиков и оплаты.\n3. Касса и банк показывают остатки, переводы, проводки и исправления.\n4. Отчёты включают прибыли и убытки, баланс, оборотную ведомость, дебиторку и кредиторку.\n5. Склад автоматически считает количество и FIFO-себестоимость.\n\nКаждая запись ведётся двойной проводкой; исправление создаёт отслеживаемое сторно.",
    },
    "legal": {
        "en": "⚖️ LEGAL & PRIVACY\n\nThis bot is a bookkeeping and management-reporting tool, not legal, tax, audit, payroll, filing, or professional accounting advice. You are responsible for reviewing entries, source documents, backups, and local compliance. Country-specific tax and payroll rules require a configured compliance module and qualified review.\n\nThe bot stores accounting records and minimal Telegram account details needed for preferences and access. AI receives a question only when requested and is given no write access.",
        "uz": "⚖️ HUQUQIY VA MAXFIYLIK\n\nBu bot ombor hisobini yuritish vositasi; huquqiy, soliq yoki professional buxgalteriya maslahati emas. Yozuvlar, zaxira nusxalari va mahalliy talablarga siz javobgarsiz.\n\nBot hisob yozuvlari va sozlamalar uchun zarur minimal Telegram ma’lumotlarini saqlaydi. AI faqat so‘ralganda savolni oladi va yozish huquqiga ega emas.",
        "tr": "⚖️ YASAL VE GİZLİLİK\n\nBu bot bir stok kayıt aracıdır; hukuki, vergi veya profesyonel muhasebe tavsiyesi değildir. Kayıtları, yedekleri ve yerel uyumu kontrol etmek sizin sorumluluğunuzdadır.\n\nBot muhasebe kayıtlarını ve ayarlar için gereken asgari Telegram bilgilerini saklar. AI yalnızca istendiğinde soruyu alır ve yazma yetkisi yoktur.",
        "it": "⚖️ NOTE LEGALI E PRIVACY\n\nQuesto bot è uno strumento di registrazione del magazzino, non consulenza legale, fiscale o contabile professionale. Sei responsabile della verifica dei dati, dei backup e degli obblighi locali.\n\nIl bot conserva i dati contabili e le informazioni Telegram minime per preferenze e accesso. L’IA riceve una domanda solo su richiesta e non può modificare i dati.",
        "ru": "⚖️ ПРАВИЛА И КОНФИДЕНЦИАЛЬНОСТЬ\n\nБот предназначен для учёта склада и не является юридической, налоговой или профессиональной бухгалтерской консультацией. Вы отвечаете за проверку записей, резервные копии и соблюдение местных требований.\n\nБот хранит бухгалтерские записи и минимум данных Telegram для настроек и доступа. ИИ получает вопрос только по запросу и не может изменять записи.",
    },
    "about": {
        "en": "ℹ️ Accounter\nRelease: {version}\nOwner/operator: {owner}\nSupport: {support}\n\nDouble-entry reports and FIFO calculations are performed by the local accounting engine, not by AI.",
        "uz": "ℹ️ FIFO Accounter\nVersiya: {version}\nEgasi/operator: {owner}\nYordam: {support}\n\nFIFO hisob-kitoblari AI emas, mahalliy hisob dvigateli tomonidan bajariladi.",
        "tr": "ℹ️ FIFO Accounter\nSürüm: {version}\nSahip/işletmeci: {owner}\nDestek: {support}\n\nFIFO hesapları AI tarafından değil, yerel muhasebe motoru tarafından yapılır.",
        "it": "ℹ️ FIFO Accounter\nVersione: {version}\nProprietario/gestore: {owner}\nSupporto: {support}\n\nI calcoli FIFO sono eseguiti dal motore contabile locale, non dall’IA.",
        "ru": "ℹ️ FIFO Accounter\nВерсия: {version}\nВладелец/оператор: {owner}\nПоддержка: {support}\n\nРасчёты FIFO выполняет локальный бухгалтерский модуль, а не ИИ.",
    },
    "inventory_panel": {"en": "📦 INVENTORY\n\nView current stock or safely remove a zero-stock product.", "uz": "📦 OMBOR\n\nJoriy qoldiqni ko‘ring yoki qoldig‘i nol mahsulotni xavfsiz olib tashlang.", "tr": "📦 STOK\n\nMevcut stoku görün veya sıfır stoklu ürünü güvenle kaldırın.", "it": "📦 MAGAZZINO\n\nVisualizza le scorte o rimuovi in sicurezza un prodotto senza giacenza.", "ru": "📦 СКЛАД\n\nПосмотрите остатки или безопасно удалите товар с нулевым остатком."},
    "remove_choose": {"en": "🗑 REMOVE PRODUCT\n\nChoose an existing product. It can be removed only when its stock is zero; historical records are preserved.", "uz": "🗑 MAHSULOTNI OLIB TASHLASH\n\nMahsulotni tanlang. Faqat qoldiq nol bo‘lsa olib tashlanadi; tarix saqlanadi.", "tr": "🗑 ÜRÜNÜ KALDIR\n\nBir ürün seçin. Yalnızca stok sıfırsa kaldırılır; geçmiş kayıtlar korunur.", "it": "🗑 RIMUOVI PRODOTTO\n\nScegli un prodotto. Può essere rimosso solo con giacenza zero; lo storico resta conservato.", "ru": "🗑 УДАЛИТЬ ТОВАР\n\nВыберите товар. Его можно удалить только при нулевом остатке; история сохраняется."},
    "ai_prompt": {"en": "✨ ASK AI\n\nSend one question about FIFO Accounter or the meaning of accounting numbers. AI cannot change your records.", "uz": "✨ AI’DAN SO‘RASH\n\nFIFO Accounter yoki hisob raqamlari haqida bitta savol yuboring. AI yozuvlarni o‘zgartira olmaydi.", "tr": "✨ AI'YA SOR\n\nFIFO Accounter veya muhasebe rakamları hakkında bir soru gönderin. AI kayıtları değiştiremez.", "it": "✨ CHIEDI ALL’IA\n\nInvia una domanda su FIFO Accounter o sul significato dei valori contabili. L’IA non può modificare i dati.", "ru": "✨ СПРОСИТЬ ИИ\n\nОтправьте один вопрос о FIFO Accounter или значении показателей. ИИ не может изменять записи."},
    "ai_disabled": {"en": "AI is disabled in your Settings.", "uz": "AI Sozlamalarda o‘chirilgan.", "tr": "AI Ayarlarınızda kapalı.", "it": "L’IA è disattivata nelle Impostazioni.", "ru": "ИИ отключён в Настройках."},
    "ai_not_configured": {"en": "AI is not connected yet. The owner must add an API key before it can be enabled.", "uz": "AI hali ulanmagan. Uni yoqish uchun egasi API kalitini qo‘shishi kerak.", "tr": "AI henüz bağlı değil. Etkinleştirmek için sahibin API anahtarı eklemesi gerekir.", "it": "L’IA non è ancora collegata. Il proprietario deve aggiungere una chiave API.", "ru": "ИИ ещё не подключён. Владелец должен добавить API-ключ."},
    "owner_only": {"en": "This control is available only to the bot owner.", "uz": "Bu boshqaruv faqat bot egasiga tegishli.", "tr": "Bu kontrol yalnızca bot sahibine açıktır.", "it": "Questo controllo è disponibile solo al proprietario del bot.", "ru": "Эта функция доступна только владельцу бота."},
    "add_sku": {"en": "➕ ADD PRODUCT · 1/3\n\nSend a short SKU, for example COFFEE-1.", "uz": "➕ MAHSULOT QO‘SHISH · 1/3\n\nQisqa SKU yuboring, masalan COFFEE-1.", "tr": "➕ ÜRÜN EKLE · 1/3\n\nKısa bir SKU gönderin, örneğin COFFEE-1.", "it": "➕ AGGIUNGI PRODOTTO · 1/3\n\nInvia uno SKU breve, per esempio COFFEE-1.", "ru": "➕ ДОБАВИТЬ ТОВАР · 1/3\n\nОтправьте короткий SKU, например COFFEE-1."},
    "add_name": {"en": "➕ ADD PRODUCT · 2/3\nSKU: {sku}\n\nSend the product name.", "uz": "➕ MAHSULOT QO‘SHISH · 2/3\nSKU: {sku}\n\nMahsulot nomini yuboring.", "tr": "➕ ÜRÜN EKLE · 2/3\nSKU: {sku}\n\nÜrün adını gönderin.", "it": "➕ AGGIUNGI PRODOTTO · 2/3\nSKU: {sku}\n\nInvia il nome del prodotto.", "ru": "➕ ДОБАВИТЬ ТОВАР · 2/3\nSKU: {sku}\n\nОтправьте название товара."},
    "add_unit": {"en": "➕ ADD PRODUCT · 3/3\n\nSend the unit, for example pcs, kg, l, or box.", "uz": "➕ MAHSULOT QO‘SHISH · 3/3\n\nBirlikni yuboring: dona, kg, l yoki quti.", "tr": "➕ ÜRÜN EKLE · 3/3\n\nBirimi gönderin: adet, kg, l veya kutu.", "it": "➕ AGGIUNGI PRODOTTO · 3/3\n\nInvia l’unità: pz, kg, l o scatola.", "ru": "➕ ДОБАВИТЬ ТОВАР · 3/3\n\nОтправьте единицу: шт, кг, л или коробка."},
    "choose_product": {"en": "{title} · 1/4\n\nChoose a product or type its SKU.", "uz": "{title} · 1/4\n\nMahsulotni tanlang yoki SKU yozing.", "tr": "{title} · 1/4\n\nBir ürün seçin veya SKU'sunu yazın.", "it": "{title} · 1/4\n\nScegli un prodotto o inserisci lo SKU.", "ru": "{title} · 1/4\n\nВыберите товар или введите SKU."},
    "purchase_quantity": {"en": "📥 PURCHASE · 2/4\n{sku}\nCurrent stock: {quantity} {unit}\n\nSend the purchase quantity.", "uz": "📥 XARID · 2/4\n{sku}\nJoriy qoldiq: {quantity} {unit}\n\nXarid miqdorini yuboring.", "tr": "📥 ALIŞ · 2/4\n{sku}\nMevcut stok: {quantity} {unit}\n\nAlış miktarını gönderin.", "it": "📥 ACQUISTO · 2/4\n{sku}\nScorta attuale: {quantity} {unit}\n\nInvia la quantità acquistata.", "ru": "📥 ПОКУПКА · 2/4\n{sku}\nТекущий остаток: {quantity} {unit}\n\nОтправьте количество покупки."},
    "purchase_cost": {"en": "📥 PURCHASE · 3/4\n\nSend the cost per unit or reuse the last cost.", "uz": "📥 XARID · 3/4\n\nBirlik tannarxini yuboring yoki oxirgi tannarxni tanlang.", "tr": "📥 ALIŞ · 3/4\n\nBirim maliyetini gönderin veya son maliyeti kullanın.", "it": "📥 ACQUISTO · 3/4\n\nInvia il costo unitario o riutilizza l’ultimo costo.", "ru": "📥 ПОКУПКА · 3/4\n\nОтправьте цену за единицу или используйте последнюю."},
    "purchase_date": {"en": "📥 PURCHASE · 4/4\n\nSend the date as YYYY-MM-DD or tap Today.", "uz": "📥 XARID · 4/4\n\nSanani YYYY-MM-DD shaklida yuboring yoki Bugun tugmasini bosing.", "tr": "📥 ALIŞ · 4/4\n\nTarihi YYYY-MM-DD olarak gönderin veya Bugün'e dokunun.", "it": "📥 ACQUISTO · 4/4\n\nInvia la data come YYYY-MM-DD oppure tocca Oggi.", "ru": "📥 ПОКУПКА · 4/4\n\nОтправьте дату в формате YYYY-MM-DD или нажмите Сегодня."},
    "sale_quantity": {"en": "📤 SALE · 2/4\nAvailable: {quantity} {unit}\n\nSend the sale quantity.", "uz": "📤 SOTUV · 2/4\nMavjud: {quantity} {unit}\n\nSotuv miqdorini yuboring.", "tr": "📤 SATIŞ · 2/4\nMevcut: {quantity} {unit}\n\nSatış miktarını gönderin.", "it": "📤 VENDITA · 2/4\nDisponibile: {quantity} {unit}\n\nInvia la quantità venduta.", "ru": "📤 ПРОДАЖА · 2/4\nДоступно: {quantity} {unit}\n\nОтправьте количество продажи."},
    "sale_price": {"en": "📤 SALE · 3/4\n\nSend the price per unit, reuse the last price, or skip it.", "uz": "📤 SOTUV · 3/4\n\nBirlik narxini yuboring, oxirgi narxni tanlang yoki o‘tkazib yuboring.", "tr": "📤 SATIŞ · 3/4\n\nBirim fiyatını gönderin, son fiyatı kullanın veya atlayın.", "it": "📤 VENDITA · 3/4\n\nInvia il prezzo unitario, usa l’ultimo prezzo oppure salta.", "ru": "📤 ПРОДАЖА · 3/4\n\nОтправьте цену за единицу, используйте последнюю или пропустите."},
    "sale_date": {"en": "📤 SALE · 4/4\n\nSend the date as YYYY-MM-DD or tap Today.", "uz": "📤 SOTUV · 4/4\n\nSanani YYYY-MM-DD shaklida yuboring yoki Bugun tugmasini bosing.", "tr": "📤 SATIŞ · 4/4\n\nTarihi YYYY-MM-DD olarak gönderin veya Bugün'e dokunun.", "it": "📤 VENDITA · 4/4\n\nInvia la data come YYYY-MM-DD oppure tocca Oggi.", "ru": "📤 ПРОДАЖА · 4/4\n\nОтправьте дату в формате YYYY-MM-DD или нажмите Сегодня."},
    "report_period": {"en": "📊 Choose a report period:", "uz": "📊 Hisobot davrini tanlang:", "tr": "📊 Rapor dönemini seçin:", "it": "📊 Scegli il periodo del report:", "ru": "📊 Выберите период отчёта:"},
    "no_products": {"en": "No products yet. Add a product first.", "uz": "Hali mahsulot yo‘q. Avval mahsulot qo‘shing.", "tr": "Henüz ürün yok. Önce bir ürün ekleyin.", "it": "Nessun prodotto. Prima aggiungi un prodotto.", "ru": "Товаров пока нет. Сначала добавьте товар."},
    "review_product": {"en": "🔎 REVIEW PRODUCT\n\nSKU: {sku}\nName: {name}\nUnit: {unit}\n\nCreate this product?", "uz": "🔎 MAHSULOTNI TEKSHIRISH\n\nSKU: {sku}\nNomi: {name}\nBirlik: {unit}\n\nMahsulot yaratilsinmi?", "tr": "🔎 ÜRÜNÜ KONTROL ET\n\nSKU: {sku}\nAd: {name}\nBirim: {unit}\n\nBu ürün oluşturulsun mu?", "it": "🔎 CONTROLLA PRODOTTO\n\nSKU: {sku}\nNome: {name}\nUnità: {unit}\n\nCreare questo prodotto?", "ru": "🔎 ПРОВЕРКА ТОВАРА\n\nSKU: {sku}\nНазвание: {name}\nЕдиница: {unit}\n\nСоздать этот товар?"},
    "review_purchase": {"en": "🔎 REVIEW PURCHASE\n\nProduct: {sku}\nQuantity: {quantity}\nUnit cost: {cost}\nTotal: {total}\nDate: {date}\n\nRecord this purchase?", "uz": "🔎 XARIDNI TEKSHIRISH\n\nMahsulot: {sku}\nMiqdor: {quantity}\nBirlik tannarxi: {cost}\nJami: {total}\nSana: {date}\n\nXarid yozilsinmi?", "tr": "🔎 ALIŞI KONTROL ET\n\nÜrün: {sku}\nMiktar: {quantity}\nBirim maliyeti: {cost}\nToplam: {total}\nTarih: {date}\n\nBu alış kaydedilsin mi?", "it": "🔎 CONTROLLA ACQUISTO\n\nProdotto: {sku}\nQuantità: {quantity}\nCosto unitario: {cost}\nTotale: {total}\nData: {date}\n\nRegistrare questo acquisto?", "ru": "🔎 ПРОВЕРКА ПОКУПКИ\n\nТовар: {sku}\nКоличество: {quantity}\nЦена за единицу: {cost}\nИтого: {total}\nДата: {date}\n\nЗаписать покупку?"},
    "review_sale": {"en": "🔎 REVIEW SALE\n\nProduct: {sku}\nQuantity: {quantity}\nUnit price: {price}\nRevenue: {revenue}\nDate: {date}\n\nFIFO COGS will be calculated automatically. Record this sale?", "uz": "🔎 SOTUVNI TEKSHIRISH\n\nMahsulot: {sku}\nMiqdor: {quantity}\nBirlik narxi: {price}\nDaromad: {revenue}\nSana: {date}\n\nFIFO tannarx avtomatik hisoblanadi. Sotuv yozilsinmi?", "tr": "🔎 SATIŞI KONTROL ET\n\nÜrün: {sku}\nMiktar: {quantity}\nBirim fiyatı: {price}\nGelir: {revenue}\nTarih: {date}\n\nFIFO maliyeti otomatik hesaplanır. Satış kaydedilsin mi?", "it": "🔎 CONTROLLA VENDITA\n\nProdotto: {sku}\nQuantità: {quantity}\nPrezzo unitario: {price}\nRicavo: {revenue}\nData: {date}\n\nIl costo FIFO verrà calcolato automaticamente. Registrare la vendita?", "ru": "🔎 ПРОВЕРКА ПРОДАЖИ\n\nТовар: {sku}\nКоличество: {quantity}\nЦена за единицу: {price}\nВыручка: {revenue}\nДата: {date}\n\nСебестоимость FIFO рассчитается автоматически. Записать продажу?"},
    "confirm_or_cancel": {"en": "Please confirm, start over, or cancel.", "uz": "Tasdiqlang, qayta boshlang yoki bekor qiling.", "tr": "Onaylayın, baştan başlayın veya iptal edin.", "it": "Conferma, ricomincia oppure annulla.", "ru": "Подтвердите, начните заново или отмените."},
    "invalid_number": {"en": "{field} must be a valid number. Try again.", "uz": "{field} to‘g‘ri raqam bo‘lishi kerak. Qayta urinib ko‘ring.", "tr": "{field} geçerli bir sayı olmalıdır. Tekrar deneyin.", "it": "{field}: inserisci un numero valido e riprova.", "ru": "Поле «{field}» должно содержать число. Попробуйте снова."},
    "number_range": {"en": "{field} must be {comparison}. Try again.", "uz": "{field} {comparison} bo‘lishi kerak. Qayta urinib ko‘ring.", "tr": "{field} {comparison} olmalıdır. Tekrar deneyin.", "it": "{field} deve essere {comparison}. Riprova.", "ru": "Поле «{field}» должно быть {comparison}. Попробуйте снова."},
    "zero_or_more": {"en": "zero or greater", "uz": "nol yoki undan katta", "tr": "sıfır veya daha büyük", "it": "zero o maggiore", "ru": "не меньше нуля"},
    "greater_zero": {"en": "greater than zero", "uz": "noldan katta", "tr": "sıfırdan büyük", "it": "maggiore di zero", "ru": "больше нуля"},
    "invalid_date": {"en": "Invalid date. Use YYYY-MM-DD and try again.", "uz": "Sana noto‘g‘ri. YYYY-MM-DD shaklida qayta yuboring.", "tr": "Geçersiz tarih. YYYY-MM-DD biçimini kullanın.", "it": "Data non valida. Usa YYYY-MM-DD e riprova.", "ru": "Неверная дата. Используйте формат YYYY-MM-DD."},
    "custom_start": {"en": "CUSTOM REPORT · 1/2\n\nSend the start date as YYYY-MM-DD.", "uz": "MAXSUS HISOBOT · 1/2\n\nBoshlanish sanasini YYYY-MM-DD shaklida yuboring.", "tr": "ÖZEL RAPOR · 1/2\n\nBaşlangıç tarihini YYYY-MM-DD olarak gönderin.", "it": "REPORT PERSONALIZZATO · 1/2\n\nInvia la data iniziale come YYYY-MM-DD.", "ru": "СВОЙ ОТЧЁТ · 1/2\n\nОтправьте начальную дату в формате YYYY-MM-DD."},
    "custom_end": {"en": "CUSTOM REPORT · 2/2\n\nSend the end date as YYYY-MM-DD.", "uz": "MAXSUS HISOBOT · 2/2\n\nTugash sanasini YYYY-MM-DD shaklida yuboring.", "tr": "ÖZEL RAPOR · 2/2\n\nBitiş tarihini YYYY-MM-DD olarak gönderin.", "it": "REPORT PERSONALIZZATO · 2/2\n\nInvia la data finale come YYYY-MM-DD.", "ru": "СВОЙ ОТЧЁТ · 2/2\n\nОтправьте конечную дату в формате YYYY-MM-DD."},
    "remove_confirm": {"en": "🗑 {sku} — {name}\n\nStock: {quantity} {unit}\nHistorical purchases, sales, and journal entries will be preserved.\n\nConfirm removal?", "uz": "🗑 {sku} — {name}\n\nQoldiq: {quantity} {unit}\nXaridlar, sotuvlar va jurnal tarixi saqlanadi.\n\nOlib tashlash tasdiqlansinmi?", "tr": "🗑 {sku} — {name}\n\nStok: {quantity} {unit}\nGeçmiş alışlar, satışlar ve yevmiye kayıtları korunur.\n\nKaldırmayı onaylıyor musunuz?", "it": "🗑 {sku} — {name}\n\nGiacenza: {quantity} {unit}\nLo storico di acquisti, vendite e registrazioni sarà conservato.\n\nConfermare la rimozione?", "ru": "🗑 {sku} — {name}\n\nОстаток: {quantity} {unit}\nИстория покупок, продаж и проводок сохранится.\n\nПодтвердить удаление?"},
    "remove_success": {"en": "✅ {sku} — {name}\n\nRemoved from active inventory. Historical accounting records were preserved.", "uz": "✅ {sku} — {name}\n\nFaol ombordan olib tashlandi. Hisob tarixi saqlandi.", "tr": "✅ {sku} — {name}\n\nAktif stoktan kaldırıldı. Muhasebe geçmişi korundu.", "it": "✅ {sku} — {name}\n\nRimosso dal magazzino attivo. Lo storico contabile è stato conservato.", "ru": "✅ {sku} — {name}\n\nТовар удалён из активного склада. Бухгалтерская история сохранена."},
}


def button(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    values = BUTTONS[key]
    return values.get(language, values[DEFAULT_LANGUAGE])


def button_values(key: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(BUTTONS[key].values()))


def matches_button(value: str, key: str) -> bool:
    return value in button_values(key)


def field_name(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    values = FIELD_NAMES[key]
    return values.get(language, values[DEFAULT_LANGUAGE])


def text(key: str, language: str = DEFAULT_LANGUAGE, **values: object) -> str:
    translations = TEXT[key]
    template = translations.get(language, translations[DEFAULT_LANGUAGE])
    return template.format(**values)

from __future__ import annotations

import asyncio
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from fifo_accounting_bot.accounting_schemas import (
    BalanceSheetReport,
    OpenItemsReport,
    ProfitLossReport,
    TrialBalanceReport,
)
from fifo_accounting_bot.bot.formatters import money
from fifo_accounting_bot.bot.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGE_DISPLAY,
    button,
    button_values,
    matches_button,
    text as translated_text,
)
from fifo_accounting_bot.config import Settings
from fifo_accounting_bot.exceptions import AccountingError
from fifo_accounting_bot.services import AccountingService, InventoryService, UserService

(
    INCOME_DESCRIPTION,
    INCOME_AMOUNT,
    INCOME_ACCOUNT,
    INCOME_DATE,
    INCOME_CONFIRM,
    EXPENSE_CATEGORY,
    EXPENSE_DESCRIPTION,
    EXPENSE_AMOUNT,
    EXPENSE_ACCOUNT,
    EXPENSE_DATE,
    EXPENSE_CONFIRM,
    CONTACT_TYPE,
    CONTACT_NAME,
    CONTACT_DETAILS,
    CONTACT_CONFIRM,
    DOCUMENT_CATEGORY,
    DOCUMENT_CONTACT,
    DOCUMENT_DESCRIPTION,
    DOCUMENT_SUBTOTAL,
    DOCUMENT_TAX,
    DOCUMENT_DUE,
    DOCUMENT_CONFIRM,
    PAYMENT_DOCUMENT,
    PAYMENT_AMOUNT,
    PAYMENT_ACCOUNT,
    PAYMENT_DATE,
    PAYMENT_CONFIRM,
    TRANSFER_FROM,
    TRANSFER_TO,
    TRANSFER_AMOUNT,
    TRANSFER_DATE,
    TRANSFER_CONFIRM,
    JOURNAL_DEBIT,
    JOURNAL_CREDIT,
    JOURNAL_DESCRIPTION,
    JOURNAL_AMOUNT,
    JOURNAL_DATE,
    JOURNAL_CONFIRM,
    CORRECTION_SELECT,
    CORRECTION_REASON,
    CORRECTION_CONFIRM,
) = range(41)

EXPENSE_BUTTONS = {
    "expense_rent": "rent",
    "expense_utilities": "utilities",
    "expense_wages": "wages",
    "expense_marketing": "marketing",
    "expense_travel": "travel",
    "expense_office": "office",
    "expense_other": "other",
}

COPY: dict[str, dict[str, str]] = {
    "sales_panel": {
        "en": "💰 SALES & INCOME\n\nRecord money already received, create a customer invoice, or apply a payment to an open invoice.",
        "uz": "💰 SAVDO VA DAROMAD\n\nOlingan pulni yozing, mijoz hisob-fakturasini yarating yoki ochiq hisobga to‘lov kiriting.",
        "tr": "💰 SATIŞ VE GELİR\n\nAlınan parayı kaydedin, müşteri faturası oluşturun veya açık faturaya tahsilat girin.",
        "it": "💰 VENDITE E RICAVI\n\nRegistra un incasso, crea una fattura cliente oppure abbina un pagamento a una fattura aperta.",
        "ru": "💰 ПРОДАЖИ И ДОХОДЫ\n\nЗапишите полученный доход, создайте счёт клиенту или внесите оплату по открытому счёту.",
    },
    "expense_panel": {
        "en": "💸 BILLS & EXPENSES\n\nRecord a paid expense, enter a supplier bill, or pay an open bill.",
        "uz": "💸 HISOBLAR VA XARAJATLAR\n\nTo‘langan xarajatni, yetkazuvchi hisobini yoki ochiq hisob to‘lovini yozing.",
        "tr": "💸 FATURALAR VE GİDERLER\n\nÖdenmiş gideri, tedarikçi faturasını veya açık fatura ödemesini kaydedin.",
        "it": "💸 FATTURE E SPESE\n\nRegistra una spesa pagata, una fattura fornitore o il pagamento di una fattura aperta.",
        "ru": "💸 СЧЕТА И РАСХОДЫ\n\nЗапишите оплаченный расход, счёт поставщика или оплату открытого счёта.",
    },
    "banking_panel": {
        "en": "🏦 CASH & BANKING\n\nView balances, move money between cash and bank, post a journal, review the ledger, or reverse an incorrect entry.",
        "uz": "🏦 KASSA VA BANK\n\nQoldiqlar, pul o‘tkazmalari, provodkalar, bosh kitob va xato yozuvni bekor qilish.",
        "tr": "🏦 KASA VE BANKA\n\nBakiyeleri görün, para aktarın, yevmiye girin, defteri inceleyin veya hatalı kaydı ters çevirin.",
        "it": "🏦 CASSA E BANCA\n\nControlla i saldi, trasferisci denaro, registra una prima nota, consulta il mastro o stornare un movimento errato.",
        "ru": "🏦 КАССА И БАНК\n\nСмотрите остатки, переводите деньги, делайте проводки, просматривайте книгу или сторнируйте ошибку.",
    },
    "contacts_panel": {
        "en": "👥 CUSTOMERS & SUPPLIERS\n\nKeep reusable contact records for invoices, bills, and outstanding balances.",
        "uz": "👥 MIJOZLAR VA YETKAZUVCHILAR\n\nHisoblar va qarzdorlik uchun kontaktlarni saqlang.",
        "tr": "👥 MÜŞTERİLER VE TEDARİKÇİLER\n\nFaturalar ve bakiyeler için kişi kayıtlarını saklayın.",
        "it": "👥 CLIENTI E FORNITORI\n\nGestisci le anagrafiche riutilizzabili per fatture, pagamenti e scadenze.",
        "ru": "👥 КЛИЕНТЫ И ПОСТАВЩИКИ\n\nХраните контакты для счетов, оплат и задолженности.",
    },
    "reports_panel": {
        "en": "📈 FINANCIAL REPORTS\n\nReports come from the balanced general ledger. Profit & loss uses the current month; other reports show today’s position.",
        "uz": "📈 MOLIYAVIY HISOBOTLAR\n\nHisobotlar balanslangan bosh kitobdan olinadi. Foyda va zarar joriy oy uchun.",
        "tr": "📈 FİNANSAL RAPORLAR\n\nRaporlar dengeli büyük defterden gelir. Kâr-zarar cari ayı gösterir.",
        "it": "📈 BILANCI E REPORT\n\nI report derivano dalla contabilità in partita doppia. Il conto economico mostra il mese corrente.",
        "ru": "📈 ФИНАНСОВЫЕ ОТЧЁТЫ\n\nОтчёты строятся по сбалансированной главной книге. Прибыли и убытки — за текущий месяц.",
    },
    "description": {
        "en": "Send a clear description.", "uz": "Aniq tavsif yuboring.", "tr": "Açık bir açıklama gönderin.", "it": "Invia una descrizione chiara.", "ru": "Отправьте понятное описание."
    },
    "amount": {
        "en": "Send the amount using a dot for decimals.", "uz": "Summani yuboring, kasr uchun nuqta ishlating.", "tr": "Tutarı gönderin; ondalık için nokta kullanın.", "it": "Invia l’importo usando il punto per i decimali.", "ru": "Отправьте сумму; для дробной части используйте точку."
    },
    "choose_account": {
        "en": "Choose Cash or Bank.", "uz": "Kassa yoki Bankni tanlang.", "tr": "Kasa veya Banka seçin.", "it": "Scegli Cassa o Banca.", "ru": "Выберите Кассу или Банк."
    },
    "date": {
        "en": "Send the date as YYYY-MM-DD or tap Today.", "uz": "Sanani YYYY-MM-DD shaklida yuboring yoki Bugun tugmasini bosing.", "tr": "Tarihi YYYY-MM-DD olarak gönderin veya Bugün'e dokunun.", "it": "Invia la data come YYYY-MM-DD oppure tocca Oggi.", "ru": "Отправьте дату ГГГГ-ММ-ДД или нажмите Сегодня."
    },
    "expense_category": {
        "en": "Choose the expense category.", "uz": "Xarajat turini tanlang.", "tr": "Gider kategorisini seçin.", "it": "Scegli la categoria di spesa.", "ru": "Выберите категорию расхода."
    },
    "contact_type": {
        "en": "Is this a customer, supplier, or both?", "uz": "Bu mijozmi, yetkazuvchimi yoki ikkalasimi?", "tr": "Müşteri, tedarikçi veya her ikisi mi?", "it": "È un cliente, un fornitore o entrambi?", "ru": "Это клиент, поставщик или оба?"
    },
    "contact_name": {
        "en": "Send the legal or display name.", "uz": "Rasmiy yoki ko‘rinadigan nomni yuboring.", "tr": "Yasal veya görünen adı gönderin.", "it": "Invia la ragione sociale o il nome.", "ru": "Отправьте юридическое или отображаемое имя."
    },
    "contact_details": {
        "en": "Optional: send email | phone | tax ID, or tap Skip.", "uz": "Ixtiyoriy: email | telefon | soliq ID yoki O‘tkazib yuborish.", "tr": "İsteğe bağlı: e-posta | telefon | vergi no veya Atla.", "it": "Facoltativo: email | telefono | partita IVA/codice fiscale, oppure Salta.", "ru": "Необязательно: email | телефон | налоговый номер или Пропустить."
    },
    "choose_contact": {
        "en": "Choose a {role}. Add one first if the list is empty.", "uz": "{role}ni tanlang. Ro‘yxat bo‘sh bo‘lsa avval qo‘shing.", "tr": "Bir {role} seçin. Liste boşsa önce ekleyin.", "it": "Scegli un {role}. Se l’elenco è vuoto, aggiungilo prima.", "ru": "Выберите: {role}. Если список пуст, сначала добавьте контакт."
    },
    "tax_rate": {
        "en": "Send the tax rate as a percentage, for example 20, or send 0.", "uz": "Soliq foizini yuboring, masalan 20, yoki 0.", "tr": "Vergi oranını yüzde olarak gönderin, örneğin 20 veya 0.", "it": "Invia l’aliquota percentuale, per esempio 22, oppure 0.", "ru": "Отправьте ставку налога в процентах, например 20, или 0."
    },
    "due_date": {
        "en": "Send the due date as YYYY-MM-DD.", "uz": "To‘lov muddatini YYYY-MM-DD shaklida yuboring.", "tr": "Vade tarihini YYYY-MM-DD olarak gönderin.", "it": "Invia la data di scadenza come YYYY-MM-DD.", "ru": "Отправьте срок оплаты в формате ГГГГ-ММ-ДД."
    },
    "no_contacts": {
        "en": "No suitable contacts yet. Add a customer or supplier first.", "uz": "Mos kontakt yo‘q. Avval mijoz yoki yetkazuvchi qo‘shing.", "tr": "Uygun kişi yok. Önce müşteri veya tedarikçi ekleyin.", "it": "Nessun contatto adatto. Aggiungi prima un cliente o fornitore.", "ru": "Подходящих контактов нет. Сначала добавьте клиента или поставщика."
    },
    "no_documents": {
        "en": "There are no open documents to pay.", "uz": "To‘lanadigan ochiq hujjatlar yo‘q.", "tr": "Ödenecek açık belge yok.", "it": "Non ci sono documenti aperti da pagare.", "ru": "Нет открытых документов для оплаты."
    },
    "choose_document": {
        "en": "Choose the open document.", "uz": "Ochiq hujjatni tanlang.", "tr": "Açık belgeyi seçin.", "it": "Scegli il documento aperto.", "ru": "Выберите открытый документ."
    },
    "choose_debit": {
        "en": "Choose the account to DEBIT.", "uz": "DEBET hisobini tanlang.", "tr": "BORÇ hesabını seçin.", "it": "Scegli il conto da addebitare in DARE.", "ru": "Выберите счёт для ДЕБЕТА."
    },
    "choose_credit": {
        "en": "Choose the account to CREDIT.", "uz": "KREDIT hisobini tanlang.", "tr": "ALACAK hesabını seçin.", "it": "Scegli il conto da accreditare in AVERE.", "ru": "Выберите счёт для КРЕДИТА."
    },
    "correction_reason": {
        "en": "Send the reason for the correction. The entry will be reversed, never deleted.", "uz": "Tuzatish sababini yuboring. Yozuv o‘chirilmaydi, teskari provodka qilinadi.", "tr": "Düzeltme nedenini gönderin. Kayıt silinmez, ters çevrilir.", "it": "Invia il motivo. Il movimento sarà stornato, mai cancellato.", "ru": "Укажите причину. Операция будет сторнирована, а не удалена."
    },
    "saved": {
        "en": "✅ Saved and posted to the general ledger.", "uz": "✅ Saqlandi va bosh kitobga yozildi.", "tr": "✅ Kaydedildi ve büyük deftere işlendi.", "it": "✅ Salvato e contabilizzato nel libro mastro.", "ru": "✅ Сохранено и проведено в главной книге."
    },
}


def _t(key: str, language: str, **values: object) -> str:
    translations = COPY[key]
    return translations.get(language, translations["en"]).format(**values)


class AccountingMenuHandlers:
    """Button-first workflows for the general accounting modules."""

    def __init__(
        self,
        accounting: AccountingService,
        inventory: InventoryService,
        users: UserService,
        settings: Settings,
        allowed_user_ids: frozenset[int] = frozenset(),
    ) -> None:
        self._accounting = accounting
        self._inventory = inventory
        self._users = users
        self._settings = settings
        self._allowed_user_ids = allowed_user_ids

    def register(self, application: Application) -> None:
        button_filter = lambda key: filters.Regex(
            "^(?:" + "|".join(re.escape(value) for value in button_values(key)) + ")$"
        )
        cancel_filter = button_filter("cancel") | button_filter("main_menu")
        restart_filter = button_filter("start_over")
        form_text = filters.TEXT & ~filters.COMMAND & ~cancel_filter & ~restart_filter

        def state(callback):
            return [
                MessageHandler(restart_filter, self.restart),
                MessageHandler(cancel_filter, self.cancel),
                MessageHandler(form_text, callback),
            ]

        handler = ConversationHandler(
            entry_points=[
                MessageHandler(button_filter("dashboard"), self.show_accounting_dashboard),
                MessageHandler(button_filter("activity"), self.show_recent_ledger),
                MessageHandler(button_filter("money_in"), self.show_income_panel),
                MessageHandler(button_filter("money_out"), self.show_expense_panel),
                MessageHandler(button_filter("banking"), self.show_banking_panel),
                MessageHandler(button_filter("contacts"), self.show_contacts_panel),
                MessageHandler(button_filter("financial_reports"), self.show_reports_panel),
                MessageHandler(button_filter("quick_income"), self.begin_income),
                MessageHandler(button_filter("quick_expense"), self.begin_expense),
                MessageHandler(button_filter("add_contact"), self.begin_contact),
                MessageHandler(button_filter("list_contacts"), self.show_contacts),
                MessageHandler(button_filter("customer_invoice"), self.begin_invoice),
                MessageHandler(button_filter("supplier_bill"), self.begin_bill),
                MessageHandler(button_filter("receive_payment"), self.begin_invoice_payment),
                MessageHandler(button_filter("pay_bill"), self.begin_bill_payment),
                MessageHandler(button_filter("cash_balances"), self.show_cash_balances),
                MessageHandler(button_filter("transfer"), self.begin_transfer),
                MessageHandler(button_filter("manual_journal"), self.begin_journal),
                MessageHandler(button_filter("correct_transaction"), self.begin_correction),
                MessageHandler(button_filter("recent_ledger"), self.show_recent_ledger),
                MessageHandler(button_filter("profit_loss"), self.show_profit_loss),
                MessageHandler(button_filter("balance_sheet"), self.show_balance_sheet),
                MessageHandler(button_filter("trial_balance"), self.show_trial_balance),
                MessageHandler(button_filter("receivables"), self.show_receivables),
                MessageHandler(button_filter("payables"), self.show_payables),
            ],
            states={
                INCOME_DESCRIPTION: state(self.income_description),
                INCOME_AMOUNT: state(self.income_amount),
                INCOME_ACCOUNT: state(self.income_account),
                INCOME_DATE: state(self.income_date),
                INCOME_CONFIRM: state(self.confirm_income),
                EXPENSE_CATEGORY: state(self.expense_category),
                EXPENSE_DESCRIPTION: state(self.expense_description),
                EXPENSE_AMOUNT: state(self.expense_amount),
                EXPENSE_ACCOUNT: state(self.expense_account),
                EXPENSE_DATE: state(self.expense_date),
                EXPENSE_CONFIRM: state(self.confirm_expense),
                CONTACT_TYPE: state(self.contact_type),
                CONTACT_NAME: state(self.contact_name),
                CONTACT_DETAILS: state(self.contact_details),
                CONTACT_CONFIRM: state(self.confirm_contact),
                DOCUMENT_CATEGORY: state(self.document_category),
                DOCUMENT_CONTACT: state(self.document_contact),
                DOCUMENT_DESCRIPTION: state(self.document_description),
                DOCUMENT_SUBTOTAL: state(self.document_subtotal),
                DOCUMENT_TAX: state(self.document_tax),
                DOCUMENT_DUE: state(self.document_due),
                DOCUMENT_CONFIRM: state(self.confirm_document),
                PAYMENT_DOCUMENT: state(self.payment_document),
                PAYMENT_AMOUNT: state(self.payment_amount),
                PAYMENT_ACCOUNT: state(self.payment_account),
                PAYMENT_DATE: state(self.payment_date),
                PAYMENT_CONFIRM: state(self.confirm_payment),
                TRANSFER_FROM: state(self.transfer_from),
                TRANSFER_TO: state(self.transfer_to),
                TRANSFER_AMOUNT: state(self.transfer_amount),
                TRANSFER_DATE: state(self.transfer_date),
                TRANSFER_CONFIRM: state(self.confirm_transfer),
                JOURNAL_DEBIT: state(self.journal_debit),
                JOURNAL_CREDIT: state(self.journal_credit),
                JOURNAL_DESCRIPTION: state(self.journal_description),
                JOURNAL_AMOUNT: state(self.journal_amount),
                JOURNAL_DATE: state(self.journal_date),
                JOURNAL_CONFIRM: state(self.confirm_journal),
                CORRECTION_SELECT: state(self.correction_select),
                CORRECTION_REASON: state(self.correction_reason),
                CORRECTION_CONFIRM: state(self.confirm_correction),
            },
            fallbacks=[MessageHandler(cancel_filter, self.cancel)],
            allow_reentry=True,
            name="general_accounting_assistant",
        )
        application.add_handler(handler)

    async def show_accounting_dashboard(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        today = date.today()
        month_start = today.replace(day=1)
        await asyncio.to_thread(self._accounting.initialize_owner, user_id)
        profit, balance, receivables, payables, cash, stock = await asyncio.gather(
            asyncio.to_thread(
                self._accounting.profit_and_loss, user_id, month_start, today
            ),
            asyncio.to_thread(self._accounting.balance_sheet, user_id, today),
            asyncio.to_thread(self._accounting.open_items, user_id, "invoice", today),
            asyncio.to_thread(self._accounting.open_items, user_id, "bill", today),
            asyncio.to_thread(self._accounting.cash_balances, user_id, today),
            asyncio.to_thread(self._inventory.get_stock, user_id),
        )
        cash_total = sum((item.balance for item in cash), Decimal("0"))
        inventory_value = sum((item.inventory_value for item in stock), Decimal("0"))
        language = self._language(context, user_id)
        lines = [
            f"{button('dashboard', language).upper()}",
            f"As of {today.isoformat()}",
            "",
            f"💵 Cash & bank: {money(cash_total)}",
            f"📥 Receivables: {money(receivables.total_outstanding)}",
            f"📤 Payables: {money(payables.total_outstanding)}",
            f"📦 Inventory: {money(inventory_value)}",
            "",
            "THIS MONTH",
            f"Income: {money(profit.total_income)}",
            f"Expenses: {money(profit.total_expenses)}",
            f"Net profit: {money(profit.net_profit)}",
            "",
            f"Assets: {money(balance.total_assets)}",
            f"Liabilities + equity: {money(balance.total_liabilities + balance.total_equity)}",
        ]
        await self._reply(
            update, "\n".join(lines), self._main_keyboard(language, user_id)
        )
        return ConversationHandler.END

    async def show_income_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        rows = [
            [button("quick_income", language), button("customer_invoice", language)],
            [button("receive_payment", language), button("sale", language)],
            [button("main_menu", language)],
        ]
        await self._reply(update, _t("sales_panel", language), self._keyboard(rows))
        return ConversationHandler.END

    async def show_expense_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        rows = [
            [button("quick_expense", language), button("supplier_bill", language)],
            [button("pay_bill", language), button("purchase", language)],
            [button("main_menu", language)],
        ]
        await self._reply(update, _t("expense_panel", language), self._keyboard(rows))
        return ConversationHandler.END

    async def show_banking_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        rows = [
            [button("cash_balances", language), button("transfer", language)],
            [button("manual_journal", language), button("recent_ledger", language)],
            [button("correct_transaction", language)],
            [button("main_menu", language)],
        ]
        await self._reply(update, _t("banking_panel", language), self._keyboard(rows))
        return ConversationHandler.END

    async def show_contacts_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        rows = [[button("add_contact", language), button("list_contacts", language)], [button("main_menu", language)]]
        await self._reply(update, _t("contacts_panel", language), self._keyboard(rows))
        return ConversationHandler.END

    async def show_reports_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        rows = [
            [button("profit_loss", language), button("balance_sheet", language)],
            [button("trial_balance", language)],
            [button("receivables", language), button("payables", language)],
            [button("report", language)],
            [button("main_menu", language)],
        ]
        await self._reply(update, _t("reports_panel", language), self._keyboard(rows))
        return ConversationHandler.END

    async def begin_income(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._begin(update, context, "income", INCOME_DESCRIPTION, "description")

    async def income_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["accounting_draft"]["description"] = self._text(update)
        return await self._prompt(update, context, "amount", INCOME_AMOUNT)

    async def income_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._decimal(self._text(update))
        if value is None:
            return await self._retry_number(update, context, INCOME_AMOUNT)
        context.user_data["accounting_draft"]["amount"] = value
        return await self._prompt(update, context, "choose_account", INCOME_ACCOUNT, self._money_keyboard(self._language(context, update.effective_user.id)))

    async def income_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        code = self._money_account_code(self._text(update))
        if code is None:
            return INCOME_ACCOUNT
        context.user_data["accounting_draft"]["account"] = code
        return await self._prompt(update, context, "date", INCOME_DATE, self._date_keyboard(self._language(context, update.effective_user.id)))

    async def income_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._date(self._text(update))
        if value is None:
            return await self._retry_date(update, context, INCOME_DATE)
        draft = context.user_data["accounting_draft"]
        draft["date"] = value
        language = self._language(context, update.effective_user.id)
        await self._reply(update, self._review(draft, language), self._confirm_keyboard(language))
        return INCOME_CONFIRM

    async def confirm_income(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not matches_button(self._text(update), "confirm"):
            return INCOME_CONFIRM
        draft = context.user_data["accounting_draft"]
        try:
            await asyncio.to_thread(
                self._accounting.record_income,
                update.effective_user.id,
                draft["description"],
                draft["amount"],
                received_on=draft["date"],
                deposited_to=draft["account"],
            )
        except AccountingError as exc:
            return await self._error(update, context, exc)
        return await self._saved(update, context)

    async def begin_expense(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        context.user_data["accounting_draft"] = {"operation": "expense"}
        language = self._language(context, user_id)
        await self._reply(update, _t("expense_category", language), self._expense_keyboard(language))
        return EXPENSE_CATEGORY

    async def expense_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        category = self._expense_category(self._text(update))
        if category is None:
            return EXPENSE_CATEGORY
        context.user_data["accounting_draft"]["category"] = category
        return await self._prompt(update, context, "description", EXPENSE_DESCRIPTION)

    async def expense_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["accounting_draft"]["description"] = self._text(update)
        return await self._prompt(update, context, "amount", EXPENSE_AMOUNT)

    async def expense_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._decimal(self._text(update))
        if value is None:
            return await self._retry_number(update, context, EXPENSE_AMOUNT)
        context.user_data["accounting_draft"]["amount"] = value
        language = self._language(context, update.effective_user.id)
        return await self._prompt(update, context, "choose_account", EXPENSE_ACCOUNT, self._money_keyboard(language))

    async def expense_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        code = self._money_account_code(self._text(update))
        if code is None:
            return EXPENSE_ACCOUNT
        context.user_data["accounting_draft"]["account"] = code
        language = self._language(context, update.effective_user.id)
        return await self._prompt(update, context, "date", EXPENSE_DATE, self._date_keyboard(language))

    async def expense_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._date(self._text(update))
        if value is None:
            return await self._retry_date(update, context, EXPENSE_DATE)
        draft = context.user_data["accounting_draft"]
        draft["date"] = value
        language = self._language(context, update.effective_user.id)
        await self._reply(update, self._review(draft, language), self._confirm_keyboard(language))
        return EXPENSE_CONFIRM

    async def confirm_expense(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not matches_button(self._text(update), "confirm"):
            return EXPENSE_CONFIRM
        draft = context.user_data["accounting_draft"]
        try:
            await asyncio.to_thread(
                self._accounting.record_expense,
                update.effective_user.id,
                draft["description"],
                draft["amount"],
                category=draft["category"],
                paid_on=draft["date"],
                paid_from=draft["account"],
            )
        except AccountingError as exc:
            return await self._error(update, context, exc)
        return await self._saved(update, context)

    async def begin_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        context.user_data["accounting_draft"] = {"operation": "contact"}
        language = self._language(context, user_id)
        rows = [[button("contact_customer", language), button("contact_supplier", language)], [button("contact_both", language)], [button("cancel", language)]]
        await self._reply(update, _t("contact_type", language), self._keyboard(rows))
        return CONTACT_TYPE

    async def contact_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        raw = self._text(update)
        mapping = {key: value for key, value in (("contact_customer", "customer"), ("contact_supplier", "supplier"), ("contact_both", "both")) if matches_button(raw, key)}
        if not mapping:
            return CONTACT_TYPE
        context.user_data["accounting_draft"]["contact_type"] = next(iter(mapping.values()))
        return await self._prompt(update, context, "contact_name", CONTACT_NAME)

    async def contact_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["accounting_draft"]["name"] = self._text(update)
        language = self._language(context, update.effective_user.id)
        keyboard = self._keyboard([[button("skip_details", language)], [button("cancel", language)]])
        return await self._prompt(update, context, "contact_details", CONTACT_DETAILS, keyboard)

    async def contact_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        raw = self._text(update)
        values = [] if matches_button(raw, "skip_details") else [part.strip() or None for part in raw.split("|")]
        values += [None] * (3 - len(values))
        draft = context.user_data["accounting_draft"]
        draft.update({"email": values[0], "phone": values[1], "tax_id": values[2]})
        language = self._language(context, update.effective_user.id)
        await self._reply(update, self._review(draft, language), self._confirm_keyboard(language))
        return CONTACT_CONFIRM

    async def confirm_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not matches_button(self._text(update), "confirm"):
            return CONTACT_CONFIRM
        draft = context.user_data["accounting_draft"]
        try:
            await asyncio.to_thread(
                self._accounting.add_contact,
                update.effective_user.id,
                draft["contact_type"],
                draft["name"],
                email=draft.get("email"),
                phone=draft.get("phone"),
                tax_id=draft.get("tax_id"),
            )
        except AccountingError as exc:
            return await self._error(update, context, exc)
        return await self._saved(update, context)

    async def show_contacts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        contacts = await asyncio.to_thread(self._accounting.list_contacts, user_id)
        lines = [button("contacts", language).upper(), ""]
        for item in contacts:
            details = " · ".join(value for value in (item.email, item.phone, item.tax_id) if value)
            lines.append(f"• #{item.id} {item.display_name} — {item.contact_type}" + (f"\n  {details}" if details else ""))
        if not contacts:
            lines.append(_t("no_contacts", language))
        await self._reply(update, "\n".join(lines), self._contacts_keyboard(language))
        return ConversationHandler.END

    async def begin_invoice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._begin_document(update, context, "invoice")

    async def begin_bill(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        context.user_data["accounting_draft"] = {"operation": "document", "document_type": "bill"}
        language = self._language(context, user_id)
        await self._reply(update, _t("expense_category", language), self._expense_keyboard(language))
        return DOCUMENT_CATEGORY

    async def document_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        category = self._expense_category(self._text(update))
        if category is None:
            return DOCUMENT_CATEGORY
        context.user_data["accounting_draft"]["category"] = category
        return await self._show_document_contacts(update, context)

    async def _begin_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE, document_type: str) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        context.user_data["accounting_draft"] = {"operation": "document", "document_type": document_type, "category": "other"}
        return await self._show_document_contacts(update, context)

    async def _show_document_contacts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["accounting_draft"]
        role = "customer" if draft["document_type"] == "invoice" else "supplier"
        contacts = await asyncio.to_thread(self._accounting.list_contacts, update.effective_user.id, role)
        language = self._language(context, update.effective_user.id)
        if not contacts:
            await self._reply(update, _t("no_contacts", language), self._contacts_keyboard(language))
            context.user_data.pop("accounting_draft", None)
            return ConversationHandler.END
        choices = {f"#{item.id} · {item.display_name}": item.id for item in contacts}
        draft["choices"] = choices
        await self._reply(update, _t("choose_contact", language, role=role), self._choice_keyboard(list(choices), language))
        return DOCUMENT_CONTACT

    async def document_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["accounting_draft"]
        contact_id = draft["choices"].get(self._text(update))
        if contact_id is None:
            return DOCUMENT_CONTACT
        draft["contact_id"] = contact_id
        draft["contact_label"] = self._text(update)
        draft.pop("choices", None)
        return await self._prompt(update, context, "description", DOCUMENT_DESCRIPTION)

    async def document_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["accounting_draft"]["description"] = self._text(update)
        return await self._prompt(update, context, "amount", DOCUMENT_SUBTOTAL)

    async def document_subtotal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._decimal(self._text(update))
        if value is None:
            return await self._retry_number(update, context, DOCUMENT_SUBTOTAL)
        context.user_data["accounting_draft"]["subtotal"] = value
        return await self._prompt(update, context, "tax_rate", DOCUMENT_TAX)

    async def document_tax(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._decimal(self._text(update), allow_zero=True)
        if value is None or value > 100:
            return await self._retry_number(update, context, DOCUMENT_TAX)
        context.user_data["accounting_draft"]["tax_rate"] = value
        return await self._prompt(update, context, "due_date", DOCUMENT_DUE, self._date_keyboard(self._language(context, update.effective_user.id)))

    async def document_due(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._date(self._text(update))
        if value is None or value < date.today():
            return await self._retry_date(update, context, DOCUMENT_DUE)
        draft = context.user_data["accounting_draft"]
        draft["due_date"] = value
        language = self._language(context, update.effective_user.id)
        await self._reply(update, self._review(draft, language), self._confirm_keyboard(language))
        return DOCUMENT_CONFIRM

    async def confirm_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not matches_button(self._text(update), "confirm"):
            return DOCUMENT_CONFIRM
        draft = context.user_data["accounting_draft"]
        try:
            result = await asyncio.to_thread(
                self._accounting.create_document,
                update.effective_user.id,
                draft["document_type"],
                draft["contact_id"],
                draft["description"],
                draft["subtotal"],
                tax_rate=draft["tax_rate"],
                due_date=draft["due_date"],
                expense_category=draft.get("category", "other"),
            )
        except AccountingError as exc:
            return await self._error(update, context, exc)
        language = self._language(context, update.effective_user.id)
        context.user_data.pop("accounting_draft", None)
        await self._reply(update, f"✅ {result.number}\n{result.contact_name}\nTotal: {money(result.total)}\nDue: {result.due_date.isoformat()}", self._main_keyboard(language, update.effective_user.id))
        return ConversationHandler.END

    async def begin_invoice_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._begin_payment(update, context, "invoice")

    async def begin_bill_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._begin_payment(update, context, "bill")

    async def _begin_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, document_type: str) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        documents = await asyncio.to_thread(self._accounting.list_open_documents, user_id, document_type)
        language = self._language(context, user_id)
        if not documents:
            await self._reply(update, _t("no_documents", language), self._main_keyboard(language, user_id))
            return ConversationHandler.END
        choices = {f"{item.number} · {item.contact_name} · {money(item.outstanding)}": item for item in documents}
        context.user_data["accounting_draft"] = {"operation": "payment", "document_type": document_type, "choices": choices}
        await self._reply(update, _t("choose_document", language), self._choice_keyboard(list(choices), language))
        return PAYMENT_DOCUMENT

    async def payment_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["accounting_draft"]
        document = draft["choices"].get(self._text(update))
        if document is None:
            return PAYMENT_DOCUMENT
        draft.update({"document_id": document.id, "document_number": document.number, "outstanding": document.outstanding})
        draft.pop("choices", None)
        language = self._language(context, update.effective_user.id)
        rows = [[button("full_amount", language)], [button("cancel", language)]]
        await self._reply(update, f"{_t('amount', language)}\nOutstanding: {money(document.outstanding)}", self._keyboard(rows))
        return PAYMENT_AMOUNT

    async def payment_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["accounting_draft"]
        value = draft["outstanding"] if matches_button(self._text(update), "full_amount") else self._decimal(self._text(update))
        if value is None or value > draft["outstanding"]:
            return await self._retry_number(update, context, PAYMENT_AMOUNT)
        draft["amount"] = value
        language = self._language(context, update.effective_user.id)
        return await self._prompt(update, context, "choose_account", PAYMENT_ACCOUNT, self._money_keyboard(language))

    async def payment_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        code = self._money_account_code(self._text(update))
        if code is None:
            return PAYMENT_ACCOUNT
        context.user_data["accounting_draft"]["account"] = code
        language = self._language(context, update.effective_user.id)
        return await self._prompt(update, context, "date", PAYMENT_DATE, self._date_keyboard(language))

    async def payment_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._date(self._text(update))
        if value is None:
            return await self._retry_date(update, context, PAYMENT_DATE)
        draft = context.user_data["accounting_draft"]
        draft["date"] = value
        language = self._language(context, update.effective_user.id)
        await self._reply(update, self._review(draft, language), self._confirm_keyboard(language))
        return PAYMENT_CONFIRM

    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not matches_button(self._text(update), "confirm"):
            return PAYMENT_CONFIRM
        draft = context.user_data["accounting_draft"]
        try:
            result = await asyncio.to_thread(
                self._accounting.record_document_payment,
                update.effective_user.id,
                draft["document_id"],
                draft["amount"],
                paid_on=draft["date"],
                account_code=draft["account"],
            )
        except AccountingError as exc:
            return await self._error(update, context, exc)
        language = self._language(context, update.effective_user.id)
        context.user_data.pop("accounting_draft", None)
        await self._reply(update, f"✅ {result.number}\nPaid: {money(result.paid_amount)}\nOutstanding: {money(result.outstanding)}\nStatus: {result.status}", self._main_keyboard(language, update.effective_user.id))
        return ConversationHandler.END

    async def show_cash_balances(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        rows = await asyncio.to_thread(self._accounting.cash_balances, user_id)
        text = "💵 CASH & BANK\n\n" + "\n".join(f"{item.code} · {item.name}: {money(item.balance)}" for item in rows)
        await self._reply(update, text, self._banking_keyboard(language))
        return ConversationHandler.END

    async def begin_transfer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        context.user_data["accounting_draft"] = {"operation": "transfer"}
        language = self._language(context, user_id)
        await self._reply(update, "FROM\n" + _t("choose_account", language), self._money_keyboard(language))
        return TRANSFER_FROM

    async def transfer_from(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        code = self._money_account_code(self._text(update))
        if code is None:
            return TRANSFER_FROM
        context.user_data["accounting_draft"]["from_account"] = code
        language = self._language(context, update.effective_user.id)
        await self._reply(update, "TO\n" + _t("choose_account", language), self._money_keyboard(language))
        return TRANSFER_TO

    async def transfer_to(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        code = self._money_account_code(self._text(update))
        draft = context.user_data["accounting_draft"]
        if code is None or code == draft["from_account"]:
            return TRANSFER_TO
        draft["to_account"] = code
        return await self._prompt(update, context, "amount", TRANSFER_AMOUNT)

    async def transfer_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._decimal(self._text(update))
        if value is None:
            return await self._retry_number(update, context, TRANSFER_AMOUNT)
        context.user_data["accounting_draft"]["amount"] = value
        language = self._language(context, update.effective_user.id)
        return await self._prompt(update, context, "date", TRANSFER_DATE, self._date_keyboard(language))

    async def transfer_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._date(self._text(update))
        if value is None:
            return await self._retry_date(update, context, TRANSFER_DATE)
        draft = context.user_data["accounting_draft"]
        draft["date"] = value
        language = self._language(context, update.effective_user.id)
        await self._reply(update, self._review(draft, language), self._confirm_keyboard(language))
        return TRANSFER_CONFIRM

    async def confirm_transfer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not matches_button(self._text(update), "confirm"):
            return TRANSFER_CONFIRM
        draft = context.user_data["accounting_draft"]
        try:
            await asyncio.to_thread(
                self._accounting.record_transfer,
                update.effective_user.id,
                draft["amount"],
                draft["from_account"],
                draft["to_account"],
                transferred_on=draft["date"],
            )
        except AccountingError as exc:
            return await self._error(update, context, exc)
        return await self._saved(update, context)

    async def begin_journal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        accounts = await asyncio.to_thread(self._accounting.list_accounts, user_id)
        choices = {f"{item.code} · {item.name}": item.code for item in accounts}
        context.user_data["accounting_draft"] = {"operation": "journal", "choices": choices}
        language = self._language(context, user_id)
        await self._reply(update, _t("choose_debit", language), self._choice_keyboard(list(choices), language))
        return JOURNAL_DEBIT

    async def journal_debit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["accounting_draft"]
        code = draft["choices"].get(self._text(update))
        if code is None:
            return JOURNAL_DEBIT
        draft["debit_account"] = code
        language = self._language(context, update.effective_user.id)
        await self._reply(update, _t("choose_credit", language), self._choice_keyboard(list(draft["choices"]), language))
        return JOURNAL_CREDIT

    async def journal_credit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["accounting_draft"]
        code = draft["choices"].get(self._text(update))
        if code is None or code == draft["debit_account"]:
            return JOURNAL_CREDIT
        draft["credit_account"] = code
        draft.pop("choices", None)
        return await self._prompt(update, context, "description", JOURNAL_DESCRIPTION)

    async def journal_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["accounting_draft"]["description"] = self._text(update)
        return await self._prompt(update, context, "amount", JOURNAL_AMOUNT)

    async def journal_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._decimal(self._text(update))
        if value is None:
            return await self._retry_number(update, context, JOURNAL_AMOUNT)
        context.user_data["accounting_draft"]["amount"] = value
        language = self._language(context, update.effective_user.id)
        return await self._prompt(update, context, "date", JOURNAL_DATE, self._date_keyboard(language))

    async def journal_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        value = self._date(self._text(update))
        if value is None:
            return await self._retry_date(update, context, JOURNAL_DATE)
        draft = context.user_data["accounting_draft"]
        draft["date"] = value
        language = self._language(context, update.effective_user.id)
        await self._reply(update, self._review(draft, language), self._confirm_keyboard(language))
        return JOURNAL_CONFIRM

    async def confirm_journal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not matches_button(self._text(update), "confirm"):
            return JOURNAL_CONFIRM
        draft = context.user_data["accounting_draft"]
        try:
            await asyncio.to_thread(
                self._accounting.record_manual_journal,
                update.effective_user.id,
                draft["description"],
                draft["amount"],
                draft["debit_account"],
                draft["credit_account"],
                entry_date=draft["date"],
            )
        except AccountingError as exc:
            return await self._error(update, context, exc)
        return await self._saved(update, context)

    async def show_recent_ledger(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        items = await asyncio.to_thread(self._accounting.recent_transactions, user_id, 15)
        lines = ["📖 GENERAL LEDGER", ""]
        for item in items:
            status = " ↩ reversed" if item.status == "reversed" else ""
            lines.append(f"#{item.id} · {item.transaction_date.isoformat()} · {money(item.amount)}{status}\n{item.description}")
        if not items:
            lines.append("No entries yet.")
        await self._reply(update, "\n\n".join(lines), self._banking_keyboard(language))
        return ConversationHandler.END

    async def begin_correction(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        items = await asyncio.to_thread(self._accounting.recent_transactions, user_id, 12, reversible_only=True)
        language = self._language(context, user_id)
        if not items:
            await self._reply(update, "No reversible entries yet. Inventory and invoice corrections use their specialized records.", self._banking_keyboard(language))
            return ConversationHandler.END
        choices = {f"#{item.id} · {item.transaction_date.isoformat()} · {money(item.amount)} · {item.description[:35]}": item.id for item in items}
        context.user_data["accounting_draft"] = {"operation": "correction", "choices": choices}
        await self._reply(update, "Choose the entry to reverse:", self._choice_keyboard(list(choices), language))
        return CORRECTION_SELECT

    async def correction_select(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["accounting_draft"]
        transaction_id = draft["choices"].get(self._text(update))
        if transaction_id is None:
            return CORRECTION_SELECT
        draft["transaction_id"] = transaction_id
        draft["selection"] = self._text(update)
        draft.pop("choices", None)
        return await self._prompt(update, context, "correction_reason", CORRECTION_REASON)

    async def correction_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["accounting_draft"]
        draft["reason"] = self._text(update)
        language = self._language(context, update.effective_user.id)
        await self._reply(update, f"↩️ REVERSE ENTRY\n\n{draft['selection']}\nReason: {draft['reason']}\n\nCreate an auditable reversing entry?", self._confirm_keyboard(language))
        return CORRECTION_CONFIRM

    async def confirm_correction(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        if not matches_button(self._text(update), "confirm"):
            return CORRECTION_CONFIRM
        draft = context.user_data["accounting_draft"]
        try:
            await asyncio.to_thread(self._accounting.reverse_transaction, update.effective_user.id, draft["transaction_id"], draft["reason"])
        except AccountingError as exc:
            return await self._error(update, context, exc)
        return await self._saved(update, context)

    async def show_profit_loss(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        today = date.today()
        report = await asyncio.to_thread(self._accounting.profit_and_loss, user_id, today.replace(day=1), today)
        language = self._language(context, user_id)
        await self._reply(update, self._format_profit_loss(report), self._reports_keyboard(language))
        return ConversationHandler.END

    async def show_balance_sheet(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        report = await asyncio.to_thread(self._accounting.balance_sheet, user_id)
        language = self._language(context, user_id)
        await self._reply(update, self._format_balance_sheet(report), self._reports_keyboard(language))
        return ConversationHandler.END

    async def show_trial_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        report = await asyncio.to_thread(self._accounting.trial_balance, user_id)
        language = self._language(context, user_id)
        await self._reply(update, self._format_trial_balance(report), self._reports_keyboard(language))
        return ConversationHandler.END

    async def show_receivables(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._show_open_items(update, context, "invoice")

    async def show_payables(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await self._show_open_items(update, context, "bill")

    async def _show_open_items(self, update: Update, context: ContextTypes.DEFAULT_TYPE, document_type: str) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        report = await asyncio.to_thread(self._accounting.open_items, user_id, document_type)
        language = self._language(context, user_id)
        await self._reply(update, self._format_open_items(report, document_type), self._reports_keyboard(language))
        return ConversationHandler.END

    async def restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        operation = context.user_data.get("accounting_draft", {}).get("operation")
        handlers = {
            "income": self.begin_income,
            "expense": self.begin_expense,
            "contact": self.begin_contact,
            "document": self.begin_invoice if context.user_data.get("accounting_draft", {}).get("document_type") == "invoice" else self.begin_bill,
            "payment": self.begin_invoice_payment if context.user_data.get("accounting_draft", {}).get("document_type") == "invoice" else self.begin_bill_payment,
            "transfer": self.begin_transfer,
            "journal": self.begin_journal,
            "correction": self.begin_correction,
        }
        handler = handlers.get(operation)
        if handler is None:
            return await self.cancel(update, context)
        return await handler(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.pop("accounting_draft", None)
        user_id = update.effective_user.id if update.effective_user else 0
        language = self._language(context, user_id)
        await self._reply(update, translated_text("cancelled", language), self._main_keyboard(language, user_id))
        return ConversationHandler.END

    async def _begin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, operation: str, state: int, prompt_key: str) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        context.user_data["accounting_draft"] = {"operation": operation}
        return await self._prompt(update, context, prompt_key, state)

    async def _prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, state: int, keyboard: ReplyKeyboardMarkup | None = None) -> int:
        language = self._language(context, update.effective_user.id)
        await self._reply(update, _t(key, language), keyboard or self._cancel_keyboard(language))
        return state

    async def _saved(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data.pop("accounting_draft", None)
        user_id = update.effective_user.id
        language = self._language(context, user_id)
        await self._reply(update, _t("saved", language), self._main_keyboard(language, user_id))
        return ConversationHandler.END

    async def _error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: AccountingError) -> int:
        context.user_data.pop("accounting_draft", None)
        user_id = update.effective_user.id
        language = self._language(context, user_id)
        await self._reply(update, f"⚠️ {error}", self._main_keyboard(language, user_id))
        return ConversationHandler.END

    async def _retry_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE, state: int) -> int:
        language = self._language(context, update.effective_user.id)
        await self._reply(update, translated_text("invalid_number", language, field="Amount"))
        return state

    async def _retry_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE, state: int) -> int:
        language = self._language(context, update.effective_user.id)
        await self._reply(update, translated_text("invalid_date", language))
        return state

    async def _authorize(self, update: Update) -> int | None:
        user = update.effective_user
        if user is None:
            return None
        if self._allowed_user_ids and user.id not in self._allowed_user_ids:
            await self._reply(update, "This bot is private and your account is not authorized.")
            return None
        profile = await asyncio.to_thread(self._users.touch, user.id, user.username, user.full_name)
        if profile.is_blocked:
            await self._reply(update, "Access to this bot has been blocked by the owner.")
            return None
        return user.id

    def _language(self, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
        cached = context.user_data.get("language")
        if cached in LANGUAGE_DISPLAY:
            return cached
        profile = self._users.get(user_id) if user_id else None
        language = profile.language if profile and profile.language in LANGUAGE_DISPLAY else DEFAULT_LANGUAGE
        context.user_data["language"] = language
        return language

    def _main_keyboard(self, language: str, user_id: int) -> ReplyKeyboardMarkup:
        rows = [
            [button("dashboard", language)],
            [button("money_in", language), button("money_out", language)],
            [button("inventory", language), button("banking", language)],
            [button("contacts", language), button("financial_reports", language)],
            [button("activity", language), button("smart_import", language)],
            [button("help_ai", language), button("settings", language)],
        ]
        if user_id in self._settings.owner_telegram_user_ids:
            rows.append([button("owner_panel", language)])
        return self._keyboard(rows)

    def _contacts_keyboard(self, language: str) -> ReplyKeyboardMarkup:
        return self._keyboard([[button("add_contact", language), button("list_contacts", language)], [button("main_menu", language)]])

    def _banking_keyboard(self, language: str) -> ReplyKeyboardMarkup:
        return self._keyboard([[button("cash_balances", language), button("transfer", language)], [button("manual_journal", language), button("recent_ledger", language)], [button("correct_transaction", language)], [button("main_menu", language)]])

    def _reports_keyboard(self, language: str) -> ReplyKeyboardMarkup:
        return self._keyboard([[button("profit_loss", language), button("balance_sheet", language)], [button("trial_balance", language)], [button("receivables", language), button("payables", language)], [button("report", language)], [button("main_menu", language)]])

    @staticmethod
    def _keyboard(rows: list[list[str]]) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)

    def _money_keyboard(self, language: str) -> ReplyKeyboardMarkup:
        return self._keyboard([[button("cash_account", language), button("bank_account", language)], [button("cancel", language)]])

    def _expense_keyboard(self, language: str) -> ReplyKeyboardMarkup:
        keys = list(EXPENSE_BUTTONS)
        rows = [[button(key, language) for key in keys[index:index + 2]] for index in range(0, len(keys), 2)]
        rows.append([button("cancel", language)])
        return self._keyboard(rows)

    def _choice_keyboard(self, choices: list[str], language: str) -> ReplyKeyboardMarkup:
        rows = [[value] for value in choices]
        rows.append([button("cancel", language)])
        return self._keyboard(rows)

    def _date_keyboard(self, language: str) -> ReplyKeyboardMarkup:
        return self._keyboard([[button("today", language)], [button("cancel", language)]])

    def _cancel_keyboard(self, language: str) -> ReplyKeyboardMarkup:
        return self._keyboard([[button("cancel", language)]])

    def _confirm_keyboard(self, language: str) -> ReplyKeyboardMarkup:
        return self._keyboard([[button("confirm", language)], [button("start_over", language), button("cancel", language)]])

    @staticmethod
    def _decimal(raw: str, *, allow_zero: bool = False) -> Decimal | None:
        try:
            value = Decimal(raw)
        except InvalidOperation:
            return None
        if not value.is_finite() or value < 0 or (value == 0 and not allow_zero):
            return None
        return value

    @staticmethod
    def _date(raw: str) -> date | None:
        if any(raw == item for item in button_values("today")):
            return date.today()
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    @staticmethod
    def _money_account_code(raw: str) -> str | None:
        if matches_button(raw, "cash_account"):
            return "1000"
        if matches_button(raw, "bank_account"):
            return "1010"
        return None

    @staticmethod
    def _expense_category(raw: str) -> str | None:
        for key, value in EXPENSE_BUTTONS.items():
            if matches_button(raw, key):
                return value
        return None

    @staticmethod
    def _text(update: Update) -> str:
        message = update.effective_message
        return message.text.strip() if message and message.text else ""

    @staticmethod
    async def _reply(update: Update, text: str, keyboard: ReplyKeyboardMarkup | None = None) -> None:
        if update.effective_message is not None:
            await update.effective_message.reply_text(text, reply_markup=keyboard)

    @staticmethod
    def _review(draft: dict[str, object], language: str) -> str:
        title = str(draft.get("operation", "entry")).replace("_", " ").upper()
        lines = [f"🔎 {title}", ""]
        labels = {
            "description": "Description", "amount": "Amount", "account": "Account",
            "category": "Category", "contact_type": "Type", "name": "Name",
            "email": "Email", "phone": "Phone", "tax_id": "Tax ID",
            "contact_label": "Contact", "subtotal": "Subtotal", "tax_rate": "Tax %",
            "due_date": "Due", "document_number": "Document", "outstanding": "Outstanding",
            "from_account": "From", "to_account": "To", "debit_account": "Debit",
            "credit_account": "Credit", "date": "Date",
        }
        for key, label in labels.items():
            value = draft.get(key)
            if value not in (None, ""):
                if isinstance(value, Decimal):
                    value = money(value)
                elif isinstance(value, date):
                    value = value.isoformat()
                lines.append(f"{label}: {value}")
        lines.extend(["", "Confirm this balanced accounting entry?"])
        return "\n".join(lines)

    @staticmethod
    def _format_profit_loss(report: ProfitLossReport) -> str:
        lines = [f"📊 PROFIT & LOSS\n{report.period_start} — {report.period_end}", "", "INCOME"]
        lines.extend(f"• {item.name}: {money(item.balance)}" for item in report.income)
        if not report.income:
            lines.append("• —")
        lines.extend([f"Total income: {money(report.total_income)}", "", "EXPENSES"])
        lines.extend(f"• {item.name}: {money(item.balance)}" for item in report.expenses)
        if not report.expenses:
            lines.append("• —")
        lines.extend([f"Total expenses: {money(report.total_expenses)}", "", f"NET PROFIT: {money(report.net_profit)}"])
        return "\n".join(lines)

    @staticmethod
    def _format_balance_sheet(report: BalanceSheetReport) -> str:
        lines = [f"⚖️ BALANCE SHEET\nAs of {report.as_of}", "", "ASSETS"]
        lines.extend(f"• {item.name}: {money(item.balance)}" for item in report.assets)
        lines.extend([f"Total assets: {money(report.total_assets)}", "", "LIABILITIES"])
        lines.extend(f"• {item.name}: {money(item.balance)}" for item in report.liabilities)
        lines.extend([f"Total liabilities: {money(report.total_liabilities)}", "", "EQUITY"])
        lines.extend(f"• {item.name}: {money(item.balance)}" for item in report.equity)
        lines.extend([f"• Current earnings: {money(report.current_earnings)}", f"Total equity: {money(report.total_equity)}", "", f"CHECK: {money(report.total_assets)} = {money(report.total_liabilities + report.total_equity)}"])
        return "\n".join(lines)

    @staticmethod
    def _format_trial_balance(report: TrialBalanceReport) -> str:
        lines = [f"🧮 TRIAL BALANCE\nAs of {report.as_of}", "", "Account · Debit · Credit"]
        lines.extend(f"{item.code} {item.name}\n  {money(item.debit)} · {money(item.credit)}" for item in report.accounts)
        lines.extend(["", f"TOTAL: {money(report.total_debits)} · {money(report.total_credits)}"])
        return "\n".join(lines)

    @staticmethod
    def _format_open_items(report: OpenItemsReport, document_type: str) -> str:
        title = "RECEIVABLES" if document_type == "invoice" else "PAYABLES"
        lines = [f"{'📥' if document_type == 'invoice' else '📤'} {title}\nAs of {report.as_of}", ""]
        for item in report.documents:
            overdue = " · OVERDUE" if item.due_date < report.as_of else ""
            lines.append(f"• {item.number} · {item.contact_name}\n  Due {item.due_date}: {money(item.outstanding)}{overdue}")
        if not report.documents:
            lines.append("Nothing outstanding.")
        lines.extend(["", f"TOTAL OUTSTANDING: {money(report.total_outstanding)}"])
        return "\n".join(lines)

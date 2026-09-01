from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from fifo_accounting_bot import __version__
from fifo_accounting_bot.bot.formatters import (
    format_activity,
    format_dashboard,
    format_report,
    format_sale,
    format_stock,
    money,
    quantity,
)
from fifo_accounting_bot.bot.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGE_BUTTONS,
    LANGUAGE_DISPLAY,
    button,
    button_values,
    field_name,
    matches_button,
    text as translated_text,
)
from fifo_accounting_bot.bot.smart_import import SmartPayload, decode_qr_image, parse_smart_payload
from fifo_accounting_bot.config import Settings
from fifo_accounting_bot.exceptions import AccountingError, ValidationError
from fifo_accounting_bot.services import InventoryService
from fifo_accounting_bot.services.ai_helper import AIHelper
from fifo_accounting_bot.services.users import UserService

LOGGER = logging.getLogger(__name__)

DASHBOARD = button("dashboard")
ADD_PRODUCT = button("add_product")
PURCHASE = button("purchase")
SALE = button("sale")
INVENTORY = button("inventory")
ACTIVITY = button("activity")
REPORT = button("report")
SMART_IMPORT = button("smart_import")
HELP = button("help_ai")
SETTINGS = button("settings")
MONEY_IN = button("money_in")
MONEY_OUT = button("money_out")
BANKING = button("banking")
CONTACTS = button("contacts")
FINANCIAL_REPORTS = button("financial_reports")
CANCEL = button("cancel")
TODAY = button("today")
SKIP_PRICE = button("skip_price")
ALL_TIME = button("all_time")
TODAY_REPORT = button("today_report")
THIS_MONTH = button("this_month")
LAST_30_DAYS = button("last_30")
CUSTOM_RANGE = button("custom_range")
BACK_TO_MENU = button("main_menu")
TYPE_SKU = button("type_sku")
CONFIRM = button("confirm")
START_OVER = button("start_over")
BUY_SCANNED = button("buy_scanned")
SELL_SCANNED = button("sell_scanned")

(
    ADD_SKU,
    ADD_NAME,
    ADD_UNIT,
    ADD_CONFIRM,
    PURCHASE_SKU,
    PURCHASE_QUANTITY,
    PURCHASE_COST,
    PURCHASE_DATE,
    PURCHASE_CONFIRM,
    SALE_SKU,
    SALE_QUANTITY,
    SALE_PRICE,
    SALE_DATE,
    SALE_CONFIRM,
    REPORT_CHOICE,
    REPORT_START,
    REPORT_END,
    SMART_INPUT,
    SMART_ACTION,
    LANGUAGE_SELECT,
    REMOVE_SELECT,
    REMOVE_CONFIRM,
    AI_QUESTION,
) = range(23)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [DASHBOARD],
        [MONEY_IN, MONEY_OUT],
        [INVENTORY, BANKING],
        [CONTACTS, FINANCIAL_REPORTS],
        [ACTIVITY, SMART_IMPORT],
        [HELP, SETTINGS],
    ],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Choose an accounting action",
)
CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    [[CANCEL]], resize_keyboard=True, is_persistent=True
)
DATE_KEYBOARD = ReplyKeyboardMarkup(
    [[TODAY], [CANCEL]], resize_keyboard=True, is_persistent=True
)
CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    [[CONFIRM], [START_OVER, CANCEL]], resize_keyboard=True, is_persistent=True
)
REPORT_KEYBOARD = ReplyKeyboardMarkup(
    [
        [TODAY_REPORT, THIS_MONTH],
        [LAST_30_DAYS, ALL_TIME],
        [CUSTOM_RANGE],
        [BACK_TO_MENU],
    ],
    resize_keyboard=True,
    is_persistent=True,
)
SCANNED_ACTION_KEYBOARD = ReplyKeyboardMarkup(
    [[BUY_SCANNED, SELL_SCANNED], [CANCEL]],
    resize_keyboard=True,
    is_persistent=True,
)

BUTTON_HELP = """🤖 FIFO Accounter Assistant

🏠 Dashboard — instant business overview
➕ Add product — guided product setup
📥 Purchase — smart product buttons and last-cost suggestion
📤 Sale — stock check, last-price suggestion, and automatic FIFO
📦 Inventory — quantities and FIFO values
🧾 Activity — recent purchases and sales
📊 Reports — today, month, 30 days, all time, or custom
📷 QR / Smart import — scan or paste transaction data

Every write shows a confirmation card first. Dates can use 📅 Today, and ❌ Cancel always returns to the main menu."""


class GuidedMenuHandlers:
    """Modern button-first Telegram UI over the accounting service."""

    def __init__(
        self,
        service: InventoryService,
        users: UserService,
        ai: AIHelper,
        settings: Settings,
        allowed_user_ids: frozenset[int] = frozenset(),
    ) -> None:
        self._service = service
        self._users = users
        self._ai = ai
        self._settings = settings
        self._allowed_user_ids = allowed_user_ids
        self._started_at = time.monotonic()

    def register(self, application: Application) -> None:
        button_filter = lambda key: filters.Regex(
            "^(?:" + "|".join(re.escape(value) for value in button_values(key)) + ")$"
        )
        language_filter = filters.Regex(
            "^(?:" + "|".join(re.escape(value) for value in LANGUAGE_BUTTONS) + ")$"
        )
        control_filter = button_filter("cancel") | button_filter("main_menu")
        start_over_filter = button_filter("start_over")
        form_text = (
            filters.TEXT & ~filters.COMMAND & ~control_filter & ~start_over_filter
        )
        text_state = lambda callback: [
            MessageHandler(start_over_filter, self.restart),
            MessageHandler(form_text, callback),
        ]
        application.add_handler(
            ConversationHandler(
                entry_points=[
                    CommandHandler("start", self.show_menu),
                    CommandHandler("help", self.show_help),
                    MessageHandler(language_filter, self.select_language),
                    MessageHandler(button_filter("dashboard"), self.show_dashboard),
                    MessageHandler(button_filter("add_product"), self.begin_add_product),
                    MessageHandler(button_filter("purchase"), self.begin_purchase),
                    MessageHandler(button_filter("sale"), self.begin_sale),
                    MessageHandler(button_filter("inventory"), self.show_inventory_panel),
                    MessageHandler(button_filter("view_stock"), self.show_inventory),
                    MessageHandler(button_filter("remove_product"), self.begin_remove_product),
                    MessageHandler(button_filter("activity"), self.show_activity),
                    MessageHandler(button_filter("report"), self.begin_report),
                    MessageHandler(button_filter("smart_import"), self.begin_smart_import),
                    MessageHandler(button_filter("help_ai"), self.show_help),
                    MessageHandler(button_filter("guide"), self.show_guide),
                    MessageHandler(button_filter("legal"), self.show_legal),
                    MessageHandler(button_filter("about"), self.show_about),
                    MessageHandler(button_filter("ask_ai"), self.begin_ai_question),
                    MessageHandler(button_filter("explain_report"), self.explain_report),
                    MessageHandler(button_filter("settings"), self.show_settings),
                    MessageHandler(button_filter("language"), self.choose_language),
                    MessageHandler(button_filter("ai_enable"), self.enable_ai),
                    MessageHandler(button_filter("ai_disable"), self.disable_ai),
                    MessageHandler(button_filter("owner_panel"), self.show_owner_panel),
                    MessageHandler(button_filter("owner_users"), self.show_owner_users),
                    MessageHandler(button_filter("owner_health"), self.show_owner_health),
                    MessageHandler(button_filter("cancel"), self.cancel),
                    MessageHandler(button_filter("main_menu"), self.cancel),
                    MessageHandler(button_filter("start_over"), self.restart),
                ],
                states={
                    ADD_SKU: text_state(self.add_sku),
                    ADD_NAME: text_state(self.add_name),
                    ADD_UNIT: text_state(self.add_unit),
                    ADD_CONFIRM: text_state(self.confirm_add),
                    PURCHASE_SKU: text_state(self.purchase_sku),
                    PURCHASE_QUANTITY: text_state(self.purchase_quantity),
                    PURCHASE_COST: text_state(self.purchase_cost),
                    PURCHASE_DATE: text_state(self.purchase_date),
                    PURCHASE_CONFIRM: text_state(self.confirm_purchase),
                    SALE_SKU: text_state(self.sale_sku),
                    SALE_QUANTITY: text_state(self.sale_quantity),
                    SALE_PRICE: text_state(self.sale_price),
                    SALE_DATE: text_state(self.sale_date),
                    SALE_CONFIRM: text_state(self.confirm_sale),
                    REPORT_CHOICE: text_state(self.report_choice),
                    REPORT_START: text_state(self.report_start),
                    REPORT_END: text_state(self.report_end),
                    SMART_INPUT: [
                        MessageHandler(start_over_filter, self.restart),
                        MessageHandler(filters.PHOTO, self.smart_photo),
                        MessageHandler(
                            filters.Document.FileExtension("json"), self.smart_document
                        ),
                        MessageHandler(form_text, self.smart_text),
                    ],
                    SMART_ACTION: text_state(self.smart_action),
                    LANGUAGE_SELECT: [
                        MessageHandler(start_over_filter, self.restart),
                        MessageHandler(language_filter, self.select_language),
                    ],
                    REMOVE_SELECT: text_state(self.remove_product_choice),
                    REMOVE_CONFIRM: text_state(self.confirm_remove_product),
                    AI_QUESTION: text_state(self.answer_ai_question),
                },
                fallbacks=[
                    CommandHandler("cancel", self.cancel),
                    MessageHandler(button_filter("cancel"), self.cancel),
                    MessageHandler(button_filter("main_menu"), self.cancel),
                ],
                allow_reentry=True,
                name="guided_fifo_assistant",
            )
        )

    async def show_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        context.user_data.pop("guided_draft", None)
        profile = await asyncio.to_thread(self._users.get, user_id)
        if profile is None or profile.language is None:
            return await self.choose_language(update, context)
        context.user_data["language"] = profile.language
        await self._reply(
            update,
            translated_text("welcome", profile.language),
            self._main_keyboard(profile.language, user_id),
        )
        return ConversationHandler.END

    async def choose_language(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if await self._authorize(update) is None:
            return ConversationHandler.END
        keyboard = ReplyKeyboardMarkup(
            [[label] for label in LANGUAGE_BUTTONS],
            resize_keyboard=True,
            is_persistent=True,
            input_field_placeholder="Language / Til / Dil / Lingua / Язык",
        )
        await self._reply(update, translated_text("choose_language"), keyboard)
        return LANGUAGE_SELECT

    async def select_language(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = LANGUAGE_BUTTONS.get(self._text(update))
        if language is None:
            return await self.choose_language(update, context)
        await asyncio.to_thread(self._users.set_language, user_id, language)
        context.user_data["language"] = language
        context.user_data.pop("guided_draft", None)
        await self._reply(
            update,
            translated_text("welcome", language),
            self._main_keyboard(language, user_id),
        )
        return ConversationHandler.END

    async def show_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        context.user_data.pop("guided_draft", None)
        language = self._language(context, user_id)
        rows = [
            [button("guide", language), button("ask_ai", language)],
            [button("explain_report", language)],
            [button("legal", language), button("about", language)],
            [button("main_menu", language)],
        ]
        await self._reply(
            update,
            translated_text("help_panel", language),
            ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True),
        )
        return ConversationHandler.END

    async def show_guide(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        await self._reply(update, translated_text("guide", language), self._help_keyboard(language))
        return ConversationHandler.END

    async def show_legal(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        await self._reply(update, translated_text("legal", language), self._help_keyboard(language))
        return ConversationHandler.END

    async def show_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        await self._reply(
            update,
            translated_text(
                "about",
                language,
                version=__version__,
                owner=self._settings.bot_owner_name,
                support=self._settings.support_contact,
            ),
            self._help_keyboard(language),
        )
        return ConversationHandler.END

    async def show_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        profile = await asyncio.to_thread(self._users.get, user_id)
        language = self._language(context, user_id)
        is_owner = self._is_owner(user_id)
        ai_enabled = bool(profile and profile.ai_enabled and self._ai.available)
        if not self._ai.available:
            ai_status = translated_text("ai_unavailable", language)
        else:
            ai_status = translated_text("ai_on" if ai_enabled else "ai_off", language)
        role = translated_text("role_owner" if is_owner else "role_user", language)
        rows = [[button("language", language)]]
        if self._ai.available:
            rows.append([button("ai_disable" if ai_enabled else "ai_enable", language)])
        if is_owner:
            rows.append([button("owner_panel", language)])
        rows.append([button("main_menu", language)])
        await self._reply(
            update,
            translated_text(
                "settings",
                language,
                role=role,
                language_name=LANGUAGE_DISPLAY[language],
                ai=ai_status,
            ),
            ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True),
        )
        return ConversationHandler.END

    async def enable_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        if not self._ai.available:
            await self._reply(update, translated_text("ai_not_configured", language), self._settings_keyboard(language, user_id))
            return ConversationHandler.END
        await asyncio.to_thread(self._users.set_ai_enabled, user_id, True)
        return await self.show_settings(update, context)

    async def disable_ai(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        await asyncio.to_thread(self._users.set_ai_enabled, user_id, False)
        return await self.show_settings(update, context)

    async def show_inventory_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        keyboard = ReplyKeyboardMarkup(
            [
                [button("add_product", language)],
                [button("purchase", language), button("sale", language)],
                [button("view_stock", language)],
                [button("remove_product", language)],
                [button("main_menu", language)],
            ],
            resize_keyboard=True,
            is_persistent=True,
        )
        await self._reply(update, translated_text("inventory_panel", language), keyboard)
        return ConversationHandler.END

    async def begin_remove_product(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        products = await asyncio.to_thread(self._service.get_stock, user_id)
        if not products:
            await self._reply(update, format_stock(products, language), self._main_keyboard(language, user_id))
            return ConversationHandler.END
        context.user_data["guided_draft"] = {"operation": "remove_product"}
        rows = [[item.sku for item in products[index:index + 2]] for index in range(0, len(products), 2)]
        rows.append([button("cancel", language)])
        await self._reply(
            update,
            translated_text("remove_choose", language),
            ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True),
        )
        return REMOVE_SELECT

    async def remove_product_choice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        sku = self._text(update).upper()
        try:
            product = (await asyncio.to_thread(self._service.get_stock, user_id, sku))[0]
        except AccountingError as exc:
            await self._reply(update, f"⚠️ {exc}")
            return REMOVE_SELECT
        context.user_data["guided_draft"].update({"sku": sku, "name": product.name})
        await self._reply(
            update,
            translated_text(
                "remove_confirm",
                language,
                sku=product.sku,
                name=product.name,
                quantity=quantity(product.quantity),
                unit=product.unit,
            ),
            self._confirm_keyboard(language),
        )
        return REMOVE_CONFIRM

    async def confirm_remove_product(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        choice = self._text(update)
        if not matches_button(choice, "confirm"):
            language = self._language(context, update.effective_user.id)
            await self._reply(update, translated_text("confirm_or_cancel", language))
            return REMOVE_CONFIRM
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        draft = context.user_data["guided_draft"]
        try:
            product = await asyncio.to_thread(self._service.archive_product, user_id, draft["sku"])
        except AccountingError as exc:
            return await self._finish_error(update, context, exc)
        context.user_data.pop("guided_draft", None)
        await self._reply(
            update,
            translated_text(
                "remove_success",
                language,
                sku=product.sku,
                name=product.name,
            ),
            self._main_keyboard(language, user_id),
        )
        return ConversationHandler.END

    async def begin_ai_question(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        profile = await asyncio.to_thread(self._users.get, user_id)
        if not self._ai.available:
            await self._reply(update, translated_text("ai_not_configured", language), self._help_keyboard(language))
            return ConversationHandler.END
        if not profile or not profile.ai_enabled:
            await self._reply(update, translated_text("ai_disabled", language), self._help_keyboard(language))
            return ConversationHandler.END
        context.user_data["guided_draft"] = {"operation": "ai_question"}
        await self._reply(update, translated_text("ai_prompt", language), self._cancel_keyboard(language))
        return AI_QUESTION

    async def answer_ai_question(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        question = self._text(update)
        if not question or len(question) > 1500:
            await self._reply(update, "Please send a question between 1 and 1,500 characters.")
            return AI_QUESTION
        try:
            answer = await asyncio.to_thread(self._ai.explain, question, language)
        except Exception:
            LOGGER.exception("AI explanation request failed")
            await self._reply(update, "The AI helper is temporarily unavailable. Your accounting data was not changed.", self._help_keyboard(language))
            return ConversationHandler.END
        context.user_data.pop("guided_draft", None)
        await self._reply(update, f"✨ {answer}", self._help_keyboard(language))
        return ConversationHandler.END

    async def explain_report(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        profile = await asyncio.to_thread(self._users.get, user_id)
        if not self._ai.available:
            await self._reply(update, translated_text("ai_not_configured", language), self._help_keyboard(language))
            return ConversationHandler.END
        if not profile or not profile.ai_enabled:
            await self._reply(update, translated_text("ai_disabled", language), self._help_keyboard(language))
            return ConversationHandler.END
        report = await asyncio.to_thread(self._service.get_report, user_id)
        context_text = (
            f"Sales count: {report.sales_count}; units sold: {quantity(report.units_sold)}; "
            f"recorded revenue: {money(report.revenue)}; FIFO COGS: {money(report.cogs)}; "
            f"gross profit on priced sales: {money(report.gross_profit)}; "
            f"current inventory units: {quantity(report.inventory_units)}; "
            f"current FIFO inventory value: {money(report.inventory_value)}."
        )
        try:
            answer = await asyncio.to_thread(
                self._ai.explain,
                "Explain these calculated report numbers simply and mention any important limitation.",
                language,
                context_text,
            )
        except Exception:
            LOGGER.exception("AI report explanation failed")
            await self._reply(update, "The AI helper is temporarily unavailable. Your accounting data was not changed.", self._help_keyboard(language))
            return ConversationHandler.END
        await self._reply(update, f"💡 {answer}", self._help_keyboard(language))
        return ConversationHandler.END

    async def show_owner_panel(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        if not self._is_owner(user_id):
            await self._reply(update, translated_text("owner_only", language), self._main_keyboard(language, user_id))
            return ConversationHandler.END
        users = await asyncio.to_thread(self._users.list_users, 200)
        keyboard = ReplyKeyboardMarkup(
            [[button("owner_users", language), button("owner_health", language)], [button("main_menu", language)]],
            resize_keyboard=True,
            is_persistent=True,
        )
        await self._reply(
            update,
            f"🛡 OWNER PANEL\n\n👥 Registered users: {len(users)}\n🤖 AI service: {'connected' if self._ai.available else 'not connected'}\n🔐 Access: owner-only",
            keyboard,
        )
        return ConversationHandler.END

    async def show_owner_users(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        if not self._is_owner(user_id):
            await self._reply(update, translated_text("owner_only", language), self._main_keyboard(language, user_id))
            return ConversationHandler.END
        users = await asyncio.to_thread(self._users.list_users, 30)
        lines = ["👥 USERS", ""]
        for item in users:
            name = item.display_name or "Unnamed"
            username = f"@{item.username}" if item.username else "no username"
            role = "Owner" if self._is_owner(item.telegram_user_id) else "User"
            state = "blocked" if item.is_blocked else "active"
            lines.append(f"• {name} · {username}\n  ID {item.telegram_user_id} · {role} · {state}")
        if not users:
            lines.append("No registered users yet.")
        await self._reply(update, "\n".join(lines), self._owner_keyboard(language))
        return ConversationHandler.END

    async def show_owner_health(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        user_id = await self._authorize(update)
        if user_id is None:
            return ConversationHandler.END
        language = self._language(context, user_id)
        if not self._is_owner(user_id):
            await self._reply(update, translated_text("owner_only", language), self._main_keyboard(language, user_id))
            return ConversationHandler.END
        report = await asyncio.to_thread(self._service.get_report, user_id)
        uptime_seconds = int(time.monotonic() - self._started_at)
        await self._reply(
            update,
            f"🩺 BOT HEALTH\n\n✅ Bot process: running\n✅ Database: connected\n⏱ Uptime: {uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m\n📦 Inventory units: {quantity(report.inventory_units)}\n🧠 AI: {'connected' if self._ai.available else 'not connected'}\n🏷 Version: {__version__}",
            self._owner_keyboard(language),
        )
        return ConversationHandler.END

    async def show_dashboard(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        owner_id = await self._authorize(update)
        if owner_id is None:
            return ConversationHandler.END
        context.user_data.pop("guided_draft", None)
        language = self._language(context, owner_id)
        try:
            stock, report = await asyncio.gather(
                asyncio.to_thread(self._service.get_stock, owner_id),
                asyncio.to_thread(self._service.get_report, owner_id),
            )
        except AccountingError as exc:
            return await self._finish_error(update, context, exc)
        await self._reply(update, format_dashboard(stock, report, language), self._main_keyboard(language, owner_id))
        return ConversationHandler.END

    async def show_inventory(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        owner_id = await self._authorize(update)
        if owner_id is None:
            return ConversationHandler.END
        context.user_data.pop("guided_draft", None)
        language = self._language(context, owner_id)
        try:
            lines = await asyncio.to_thread(self._service.get_stock, owner_id)
        except AccountingError as exc:
            return await self._finish_error(update, context, exc)
        await self._reply(update, format_stock(lines, language), self._main_keyboard(language, owner_id))
        return ConversationHandler.END

    async def show_activity(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        owner_id = await self._authorize(update)
        if owner_id is None:
            return ConversationHandler.END
        context.user_data.pop("guided_draft", None)
        language = self._language(context, owner_id)
        activity = await asyncio.to_thread(
            self._service.get_recent_activity, owner_id, 10
        )
        await self._reply(update, format_activity(activity, language), self._main_keyboard(language, owner_id))
        return ConversationHandler.END

    async def begin_add_product(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if await self._authorize(update) is None:
            return ConversationHandler.END
        language = self._language(context, update.effective_user.id)
        context.user_data["guided_draft"] = {"operation": "add_product"}
        await self._reply(
            update,
            translated_text("add_sku", language),
            self._cancel_keyboard(language),
        )
        return ADD_SKU

    async def add_sku(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        sku = self._text(update).upper()
        if not sku or len(sku) > 64:
            await self._reply(update, "SKU must contain 1 to 64 characters. Try again.")
            return ADD_SKU
        context.user_data["guided_draft"]["sku"] = sku
        language = self._language(context, update.effective_user.id)
        await self._reply(update, translated_text("add_name", language, sku=sku))
        return ADD_NAME

    async def add_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        name = self._text(update)
        if not name or len(name) > 200:
            await self._reply(update, "Name must contain 1 to 200 characters. Try again.")
            return ADD_NAME
        context.user_data["guided_draft"]["name"] = name
        language = self._language(context, update.effective_user.id)
        await self._reply(
            update,
            translated_text("add_unit", language),
        )
        return ADD_UNIT

    async def add_unit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        unit = self._text(update).lower()
        if not unit or len(unit) > 32:
            await self._reply(update, "Unit must contain 1 to 32 characters. Try again.")
            return ADD_UNIT
        context.user_data["guided_draft"]["unit"] = unit
        await self._show_add_confirmation(update, context)
        return ADD_CONFIRM

    async def confirm_add(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        choice = self._text(update)
        if matches_button(choice, "start_over"):
            return await self.begin_add_product(update, context)
        if not matches_button(choice, "confirm"):
            await self._reply(update, translated_text("confirm_or_cancel", self._language(context, update.effective_user.id)))
            return ADD_CONFIRM
        draft = context.user_data["guided_draft"]
        try:
            result = await asyncio.to_thread(
                self._service.add_product,
                update.effective_user.id,
                draft["sku"],
                draft["name"],
                draft["unit"],
            )
        except AccountingError as exc:
            return await self._finish_error(update, context, exc)
        context.user_data.pop("guided_draft", None)
        language = self._language(context, update.effective_user.id)
        await self._reply(
            update,
            f"✅ Product created\n\n{result.sku} — {result.name}\nUnit: {result.unit}",
            self._main_keyboard(language, update.effective_user.id),
        )
        return ConversationHandler.END

    async def begin_purchase(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        owner_id = await self._authorize(update)
        if owner_id is None:
            return ConversationHandler.END
        context.user_data["guided_draft"] = {"operation": "purchase"}
        language = self._language(context, owner_id)
        return await self._ask_for_product(update, context, owner_id, PURCHASE_SKU, button("purchase", language))

    async def purchase_sku(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        sku = self._text(update).upper()
        language = self._language(context, update.effective_user.id)
        if matches_button(self._text(update), "type_sku"):
            await self._reply(update, "Type the product SKU:", self._cancel_keyboard(language))
            return PURCHASE_SKU
        try:
            stock = await asyncio.to_thread(
                self._service.get_stock, update.effective_user.id, sku
            )
        except AccountingError as exc:
            await self._reply(update, f"{exc}\n\nChoose or type another SKU.")
            return PURCHASE_SKU
        last_cost = await asyncio.to_thread(
            self._service.get_last_purchase_unit_cost, update.effective_user.id, sku
        )
        draft = context.user_data["guided_draft"]
        draft.update({"sku": sku, "last_cost": last_cost})
        await self._reply(
            update,
            translated_text("purchase_quantity", language, sku=sku, quantity=quantity(stock[0].quantity), unit=stock[0].unit),
            self._cancel_keyboard(language),
        )
        return PURCHASE_QUANTITY

    async def purchase_quantity(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        language = self._language(context, update.effective_user.id)
        parsed = _parse_decimal(self._text(update), "quantity", language, allow_zero=False)
        if isinstance(parsed, str):
            await self._reply(update, parsed)
            return PURCHASE_QUANTITY
        draft = context.user_data["guided_draft"]
        draft["quantity"] = parsed
        language = self._language(context, update.effective_user.id)
        keyboard = self._cancel_keyboard(language)
        if draft.get("last_cost") is not None:
            label = f"Use last cost · {money(draft['last_cost'])}"
            draft["last_cost_button"] = label
            keyboard = ReplyKeyboardMarkup(
                [[label], [button("cancel", language)]], resize_keyboard=True, is_persistent=True
            )
        await self._reply(
            update,
            translated_text("purchase_cost", language),
            keyboard,
        )
        return PURCHASE_COST

    async def purchase_cost(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        draft = context.user_data["guided_draft"]
        raw = self._text(update)
        if raw == draft.get("last_cost_button"):
            parsed = draft["last_cost"]
        else:
            parsed = _parse_decimal(raw, "unit_cost", self._language(context, update.effective_user.id), allow_zero=True)
            if isinstance(parsed, str):
                await self._reply(update, parsed)
                return PURCHASE_COST
        draft["unit_cost"] = parsed
        await self._reply(
            update,
            translated_text("purchase_date", self._language(context, update.effective_user.id)),
            self._date_keyboard(self._language(context, update.effective_user.id)),
        )
        return PURCHASE_DATE

    async def purchase_date(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        parsed = _parse_date_or_today(self._text(update), self._language(context, update.effective_user.id))
        if isinstance(parsed, str):
            await self._reply(update, parsed)
            return PURCHASE_DATE
        context.user_data["guided_draft"]["date"] = parsed
        await self._show_purchase_confirmation(update, context)
        return PURCHASE_CONFIRM

    async def confirm_purchase(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        choice = self._text(update)
        if matches_button(choice, "start_over"):
            return await self.begin_purchase(update, context)
        if not matches_button(choice, "confirm"):
            await self._reply(update, translated_text("confirm_or_cancel", self._language(context, update.effective_user.id)))
            return PURCHASE_CONFIRM
        draft = context.user_data["guided_draft"]
        try:
            result = await asyncio.to_thread(
                self._service.record_purchase,
                update.effective_user.id,
                draft["sku"],
                draft["quantity"],
                draft["unit_cost"],
                draft["date"],
            )
            stock = await asyncio.to_thread(
                self._service.get_stock, update.effective_user.id, draft["sku"]
            )
        except AccountingError as exc:
            return await self._finish_error(update, context, exc)
        context.user_data.pop("guided_draft", None)
        language = self._language(context, update.effective_user.id)
        await self._reply(
            update,
            f"✅ Purchase recorded\n\nBatch #{result.batch_id} · {result.sku}\n"
            f"{quantity(result.quantity)} × {money(result.unit_cost)} = {money(result.total_cost)}\n"
            f"New stock: {quantity(stock[0].quantity)} {stock[0].unit}",
            self._main_keyboard(language, update.effective_user.id),
        )
        return ConversationHandler.END

    async def begin_sale(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        owner_id = await self._authorize(update)
        if owner_id is None:
            return ConversationHandler.END
        context.user_data["guided_draft"] = {"operation": "sale"}
        language = self._language(context, owner_id)
        return await self._ask_for_product(update, context, owner_id, SALE_SKU, button("sale", language))

    async def sale_sku(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        sku = self._text(update).upper()
        language = self._language(context, update.effective_user.id)
        if matches_button(self._text(update), "type_sku"):
            await self._reply(update, "Type the product SKU:", self._cancel_keyboard(language))
            return SALE_SKU
        try:
            stock = await asyncio.to_thread(
                self._service.get_stock, update.effective_user.id, sku
            )
        except AccountingError as exc:
            await self._reply(update, f"{exc}\n\nChoose or type another SKU.")
            return SALE_SKU
        if stock[0].quantity <= 0:
            await self._reply(update, f"{sku} is out of stock. Choose another product.")
            return SALE_SKU
        last_price = await asyncio.to_thread(
            self._service.get_last_sale_unit_price, update.effective_user.id, sku
        )
        draft = context.user_data["guided_draft"]
        draft.update(
            {"sku": sku, "available": stock[0].quantity, "unit": stock[0].unit, "last_price": last_price}
        )
        await self._reply(
            update,
            translated_text("sale_quantity", language, quantity=quantity(stock[0].quantity), unit=stock[0].unit),
            self._cancel_keyboard(language),
        )
        return SALE_QUANTITY

    async def sale_quantity(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        language = self._language(context, update.effective_user.id)
        parsed = _parse_decimal(self._text(update), "quantity", language, allow_zero=False)
        if isinstance(parsed, str):
            await self._reply(update, parsed)
            return SALE_QUANTITY
        draft = context.user_data["guided_draft"]
        if parsed > draft["available"]:
            await self._reply(
                update,
                f"Not enough stock. Available: {quantity(draft['available'])} {draft['unit']}. Try a smaller quantity.",
            )
            return SALE_QUANTITY
        draft["quantity"] = parsed
        rows: list[list[str]] = []
        if draft.get("last_price") is not None:
            label = f"Use last price · {money(draft['last_price'])}"
            draft["last_price_button"] = label
            rows.append([label])
        language = self._language(context, update.effective_user.id)
        rows.extend([[button("skip_price", language)], [button("cancel", language)]])
        await self._reply(
            update,
            translated_text("sale_price", language),
            ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True),
        )
        return SALE_PRICE

    async def sale_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        draft = context.user_data["guided_draft"]
        raw = self._text(update)
        if matches_button(raw, "skip_price"):
            price: Decimal | None = None
        elif raw == draft.get("last_price_button"):
            price = draft["last_price"]
        else:
            parsed = _parse_decimal(raw, "sale_price", self._language(context, update.effective_user.id), allow_zero=True)
            if isinstance(parsed, str):
                await self._reply(update, parsed)
                return SALE_PRICE
            price = parsed
        draft["unit_sale_price"] = price
        await self._reply(
            update,
            translated_text("sale_date", self._language(context, update.effective_user.id)),
            self._date_keyboard(self._language(context, update.effective_user.id)),
        )
        return SALE_DATE

    async def sale_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        parsed = _parse_date_or_today(self._text(update), self._language(context, update.effective_user.id))
        if isinstance(parsed, str):
            await self._reply(update, parsed)
            return SALE_DATE
        context.user_data["guided_draft"]["date"] = parsed
        await self._show_sale_confirmation(update, context)
        return SALE_CONFIRM

    async def confirm_sale(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        choice = self._text(update)
        if matches_button(choice, "start_over"):
            return await self.begin_sale(update, context)
        if not matches_button(choice, "confirm"):
            await self._reply(update, translated_text("confirm_or_cancel", self._language(context, update.effective_user.id)))
            return SALE_CONFIRM
        draft = context.user_data["guided_draft"]
        try:
            result = await asyncio.to_thread(
                self._service.record_sale,
                update.effective_user.id,
                draft["sku"],
                draft["quantity"],
                draft["unit_sale_price"],
                draft["date"],
            )
            stock = await asyncio.to_thread(
                self._service.get_stock, update.effective_user.id, draft["sku"]
            )
        except AccountingError as exc:
            return await self._finish_error(update, context, exc)
        warning = ""
        if stock[0].quantity <= 0:
            warning = "\n\n⚠️ This product is now out of stock."
        elif stock[0].quantity <= result.quantity:
            warning = f"\n\n⚠️ Low stock: {quantity(stock[0].quantity)} {stock[0].unit} remaining."
        context.user_data.pop("guided_draft", None)
        language = self._language(context, update.effective_user.id)
        await self._reply(
            update,
            f"✅ {format_sale(result, language)}\nRemaining: {quantity(stock[0].quantity)} {stock[0].unit}{warning}",
            self._main_keyboard(language, update.effective_user.id),
        )
        return ConversationHandler.END

    async def begin_report(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if await self._authorize(update) is None:
            return ConversationHandler.END
        language = self._language(context, update.effective_user.id)
        context.user_data["guided_draft"] = {"operation": "report"}
        await self._reply(update, translated_text("report_period", language), self._report_keyboard(language))
        return REPORT_CHOICE

    async def report_choice(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        choice = self._text(update)
        today = date.today()
        if matches_button(choice, "all_time"):
            return await self._send_report(update, context, None, None)
        if matches_button(choice, "today_report"):
            return await self._send_report(update, context, today, today)
        if matches_button(choice, "this_month"):
            return await self._send_report(update, context, today.replace(day=1), today)
        if matches_button(choice, "last_30"):
            return await self._send_report(update, context, today - timedelta(days=29), today)
        if matches_button(choice, "custom_range"):
            await self._reply(
                update,
                translated_text("custom_start", self._language(context, update.effective_user.id)),
                self._cancel_keyboard(self._language(context, update.effective_user.id)),
            )
            return REPORT_START
        await self._reply(update, "Please choose one of the report buttons.")
        return REPORT_CHOICE

    async def report_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        parsed = _parse_iso_date(self._text(update), self._language(context, update.effective_user.id))
        if isinstance(parsed, str):
            await self._reply(update, parsed)
            return REPORT_START
        context.user_data["guided_draft"]["period_start"] = parsed
        await self._reply(update, translated_text("custom_end", self._language(context, update.effective_user.id)))
        return REPORT_END

    async def report_end(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        parsed = _parse_iso_date(self._text(update), self._language(context, update.effective_user.id))
        if isinstance(parsed, str):
            await self._reply(update, parsed)
            return REPORT_END
        return await self._send_report(
            update,
            context,
            context.user_data["guided_draft"]["period_start"],
            parsed,
        )

    async def begin_smart_import(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if await self._authorize(update) is None:
            return ConversationHandler.END
        language = self._language(context, update.effective_user.id)
        context.user_data["guided_draft"] = {"operation": "smart_import"}
        await self._reply(
            update,
            "📷 QR / Smart import\n\nSend a clear QR photo, a .json file, a plain SKU, a fifo:// payload, or a JSON transaction.\n\nExample:\n"
            '{"type":"purchase","sku":"COFFEE-1","quantity":10,"unit_cost":8.5,"date":"2026-08-31"}\n\n'
            "Nothing is saved until you confirm.",
            self._cancel_keyboard(language),
        )
        return SMART_INPUT

    async def smart_photo(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        try:
            telegram_file = await update.effective_message.photo[-1].get_file()
            image_bytes = bytes(await telegram_file.download_as_bytearray())
            raw = await asyncio.to_thread(decode_qr_image, image_bytes)
            payload = parse_smart_payload(raw)
        except AccountingError as exc:
            await self._reply(update, f"Could not scan that QR: {exc}\n\nTry another image or paste the data.")
            return SMART_INPUT
        return await self._prepare_smart_payload(update, context, payload)

    async def smart_document(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        document = update.effective_message.document
        if document.file_size and document.file_size > 64 * 1024:
            await self._reply(update, "JSON files must be 64 KB or smaller. Try another file.")
            return SMART_INPUT
        try:
            telegram_file = await document.get_file()
            raw = bytes(await telegram_file.download_as_bytearray()).decode("utf-8")
            payload = parse_smart_payload(raw)
        except UnicodeDecodeError:
            await self._reply(update, "That file is not valid UTF-8 JSON. Try another file.")
            return SMART_INPUT
        except AccountingError as exc:
            await self._reply(update, f"Could not import that file: {exc}\n\nTry again or cancel.")
            return SMART_INPUT
        return await self._prepare_smart_payload(update, context, payload)

    async def smart_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        try:
            payload = parse_smart_payload(self._text(update))
        except AccountingError as exc:
            await self._reply(update, f"Could not read that data: {exc}\n\nTry again or cancel.")
            return SMART_INPUT
        return await self._prepare_smart_payload(update, context, payload)

    async def smart_action(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        choice = self._text(update)
        previous = context.user_data["guided_draft"]
        sku = previous["sku"]
        language = self._language(context, update.effective_user.id)
        if matches_button(choice, "buy_scanned"):
            context.user_data["guided_draft"] = {
                "operation": "purchase",
                "sku": sku,
                "last_cost": await asyncio.to_thread(
                    self._service.get_last_purchase_unit_cost,
                    update.effective_user.id,
                    sku,
                ),
            }
            await self._reply(update, f"📥 Purchase · {sku}\n\nSend the quantity.", self._cancel_keyboard(language))
            return PURCHASE_QUANTITY
        if matches_button(choice, "sell_scanned"):
            stock = await asyncio.to_thread(
                self._service.get_stock, update.effective_user.id, sku
            )
            if stock[0].quantity <= 0:
                await self._reply(update, f"{sku} is out of stock.", self._main_keyboard(language, update.effective_user.id))
                return ConversationHandler.END
            context.user_data["guided_draft"] = {
                "operation": "sale",
                "sku": sku,
                "available": stock[0].quantity,
                "unit": stock[0].unit,
                "last_price": await asyncio.to_thread(
                    self._service.get_last_sale_unit_price,
                    update.effective_user.id,
                    sku,
                ),
            }
            await self._reply(
                update,
                f"📤 Sale · {sku}\nAvailable: {quantity(stock[0].quantity)} {stock[0].unit}\n\nSend the quantity.",
                self._cancel_keyboard(language),
            )
            return SALE_QUANTITY
        await self._reply(update, "Choose Purchase, Sale, or Cancel.")
        return SMART_ACTION

    async def _prepare_smart_payload(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        payload: SmartPayload,
    ) -> int:
        owner_id = update.effective_user.id
        if payload.kind == "lookup":
            try:
                stock = await asyncio.to_thread(self._service.get_stock, owner_id, payload.sku)
            except AccountingError as exc:
                await self._reply(update, f"QR detected {payload.sku}, but {exc}", self._cancel_keyboard(self._language(context, owner_id)))
                return SMART_INPUT
            context.user_data["guided_draft"] = {
                "operation": "smart_lookup",
                "sku": payload.sku,
            }
            await self._reply(
                update,
                f"✅ QR recognized\n\n{stock[0].sku} — {stock[0].name}\n"
                f"Stock: {quantity(stock[0].quantity)} {stock[0].unit}\n"
                f"FIFO value: {money(stock[0].inventory_value)}\n\nWhat should I do?",
                self._scanned_keyboard(self._language(context, owner_id)),
            )
            return SMART_ACTION

        if payload.kind == "product":
            context.user_data["guided_draft"] = {
                "operation": "add_product",
                "sku": payload.sku,
                "name": payload.name,
                "unit": payload.unit,
            }
            await self._show_add_confirmation(update, context, source="QR / Smart import")
            return ADD_CONFIRM

        try:
            stock = await asyncio.to_thread(self._service.get_stock, owner_id, payload.sku)
        except AccountingError as exc:
            await self._reply(update, f"Import rejected: {exc}", self._main_keyboard(self._language(context, owner_id), owner_id))
            return ConversationHandler.END

        if payload.kind == "purchase":
            context.user_data["guided_draft"] = {
                "operation": "purchase",
                "sku": payload.sku,
                "quantity": payload.quantity,
                "unit_cost": payload.unit_cost,
                "date": payload.occurred_on or date.today(),
            }
            await self._show_purchase_confirmation(update, context, source="QR / Smart import")
            return PURCHASE_CONFIRM

        if payload.quantity is None or payload.quantity > stock[0].quantity:
            await self._reply(
                update,
                f"Import rejected: requested {quantity(payload.quantity or Decimal('0'))}, but only "
                f"{quantity(stock[0].quantity)} {stock[0].unit} is available.",
                self._main_keyboard(self._language(context, owner_id), owner_id),
            )
            return ConversationHandler.END
        context.user_data["guided_draft"] = {
            "operation": "sale",
            "sku": payload.sku,
            "quantity": payload.quantity,
            "unit_sale_price": payload.unit_price,
            "date": payload.occurred_on or date.today(),
            "available": stock[0].quantity,
            "unit": stock[0].unit,
        }
        await self._show_sale_confirmation(update, context, source="QR / Smart import")
        return SALE_CONFIRM

    async def _ask_for_product(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, owner_id: int, state: int, title: str
    ) -> int:
        language = self._language(context, owner_id)
        products = await asyncio.to_thread(self._service.get_stock, owner_id)
        if not products:
            await self._reply(
                update,
                translated_text("no_products", language),
                self._main_keyboard(language, owner_id),
            )
            return ConversationHandler.END
        rows = [[line.sku for line in products[index : index + 2]] for index in range(0, min(len(products), 10), 2)]
        rows.extend([[button("type_sku", language)], [button("cancel", language)]])
        await self._reply(
            update,
            translated_text("choose_product", language, title=title),
            ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True),
        )
        return state

    async def _show_add_confirmation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        source: str = "Guided form",
    ) -> None:
        draft = context.user_data["guided_draft"]
        language = self._language(context, update.effective_user.id)
        await self._reply(
            update,
            translated_text(
                "review_product",
                language,
                sku=draft["sku"],
                name=draft["name"],
                unit=draft["unit"],
            ),
            self._confirm_keyboard(language),
        )

    async def _show_purchase_confirmation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        source: str = "Guided form",
    ) -> None:
        draft = context.user_data["guided_draft"]
        language = self._language(context, update.effective_user.id)
        total = draft["quantity"] * draft["unit_cost"]
        await self._reply(
            update,
            translated_text(
                "review_purchase",
                language,
                sku=draft["sku"],
                quantity=quantity(draft["quantity"]),
                cost=money(draft["unit_cost"]),
                total=money(total),
                date=draft["date"].isoformat(),
            ),
            self._confirm_keyboard(language),
        )

    async def _show_sale_confirmation(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        source: str = "Guided form",
    ) -> None:
        draft = context.user_data["guided_draft"]
        language = self._language(context, update.effective_user.id)
        price = draft["unit_sale_price"]
        revenue = draft["quantity"] * price if price is not None else None
        await self._reply(
            update,
            translated_text(
                "review_sale",
                language,
                sku=draft["sku"],
                quantity=quantity(draft["quantity"]),
                price=money(price) if price is not None else "—",
                revenue=money(revenue) if revenue is not None else "—",
                date=draft["date"].isoformat(),
            ),
            self._confirm_keyboard(language),
        )

    async def _send_report(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        period_start: date | None,
        period_end: date | None,
    ) -> int:
        try:
            report = await asyncio.to_thread(
                self._service.get_report,
                update.effective_user.id,
                period_start,
                period_end,
            )
        except AccountingError as exc:
            return await self._finish_error(update, context, exc)
        context.user_data.pop("guided_draft", None)
        language = self._language(context, update.effective_user.id)
        await self._reply(update, format_report(report, language), self._main_keyboard(language, update.effective_user.id))
        return ConversationHandler.END

    async def restart(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        operation = context.user_data.get("guided_draft", {}).get("operation")
        restart_handlers = {
            "add_product": self.begin_add_product,
            "purchase": self.begin_purchase,
            "sale": self.begin_sale,
            "report": self.begin_report,
            "smart_import": self.begin_smart_import,
            "smart_lookup": self.begin_smart_import,
            "remove_product": self.begin_remove_product,
            "ai_question": self.begin_ai_question,
        }
        handler = restart_handlers.get(operation)
        if handler is None:
            return await self.cancel(update, context)
        return await handler(update, context)

    async def cancel(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        context.user_data.pop("guided_draft", None)
        user_id = update.effective_user.id if update.effective_user else 0
        language = self._language(context, user_id)
        await self._reply(update, translated_text("cancelled", language), self._main_keyboard(language, user_id))
        return ConversationHandler.END

    async def _finish_error(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        error: AccountingError,
    ) -> int:
        context.user_data.pop("guided_draft", None)
        user_id = update.effective_user.id if update.effective_user else 0
        language = self._language(context, user_id)
        await self._reply(update, f"⚠️ {error}", self._main_keyboard(language, user_id))
        return ConversationHandler.END

    async def _authorize(self, update: Update) -> int | None:
        user = update.effective_user
        if user is None:
            await self._reply(update, "This action must be sent by a Telegram user.")
            return None
        if self._allowed_user_ids and user.id not in self._allowed_user_ids:
            LOGGER.warning("Rejected Telegram user ID %s", user.id)
            await self._reply(update, "This bot is private and your account is not authorized.")
            return None
        profile = await asyncio.to_thread(
            self._users.touch,
            user.id,
            user.username,
            user.full_name,
        )
        if profile.is_blocked:
            LOGGER.warning("Rejected blocked Telegram user ID %s", user.id)
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

    def _is_owner(self, user_id: int) -> bool:
        return user_id in self._settings.owner_telegram_user_ids

    def _main_keyboard(self, language: str, user_id: int) -> ReplyKeyboardMarkup:
        rows = [
            [button("dashboard", language)],
            [button("money_in", language), button("money_out", language)],
            [button("inventory", language), button("banking", language)],
            [button("contacts", language), button("financial_reports", language)],
            [button("activity", language), button("smart_import", language)],
            [button("help_ai", language), button("settings", language)],
        ]
        if self._is_owner(user_id):
            rows.append([button("owner_panel", language)])
        return ReplyKeyboardMarkup(
            rows,
            resize_keyboard=True,
            is_persistent=True,
            input_field_placeholder=button("settings", language),
        )

    @staticmethod
    def _cancel_keyboard(language: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup([[button("cancel", language)]], resize_keyboard=True, is_persistent=True)

    @staticmethod
    def _date_keyboard(language: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup([[button("today", language)], [button("cancel", language)]], resize_keyboard=True, is_persistent=True)

    @staticmethod
    def _confirm_keyboard(language: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            [[button("confirm", language)], [button("start_over", language), button("cancel", language)]],
            resize_keyboard=True,
            is_persistent=True,
        )

    @staticmethod
    def _report_keyboard(language: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            [
                [button("today_report", language), button("this_month", language)],
                [button("last_30", language), button("all_time", language)],
                [button("custom_range", language)],
                [button("main_menu", language)],
            ],
            resize_keyboard=True,
            is_persistent=True,
        )

    @staticmethod
    def _scanned_keyboard(language: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            [[button("buy_scanned", language), button("sell_scanned", language)], [button("cancel", language)]],
            resize_keyboard=True,
            is_persistent=True,
        )

    @staticmethod
    def _help_keyboard(language: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            [[button("guide", language), button("ask_ai", language)], [button("legal", language), button("about", language)], [button("main_menu", language)]],
            resize_keyboard=True,
            is_persistent=True,
        )

    def _settings_keyboard(self, language: str, user_id: int) -> ReplyKeyboardMarkup:
        rows = [[button("language", language)]]
        if self._ai.available:
            rows.append([button("ai_enable", language)])
        if self._is_owner(user_id):
            rows.append([button("owner_panel", language)])
        rows.append([button("main_menu", language)])
        return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)

    @staticmethod
    def _owner_keyboard(language: str) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            [[button("owner_users", language), button("owner_health", language)], [button("main_menu", language)]],
            resize_keyboard=True,
            is_persistent=True,
        )

    @staticmethod
    def _text(update: Update) -> str:
        message = update.effective_message
        return message.text.strip() if message and message.text else ""

    @staticmethod
    async def _reply(
        update: Update,
        text: str,
        keyboard: ReplyKeyboardMarkup | None = None,
    ) -> None:
        message = update.effective_message
        if message is not None:
            await message.reply_text(text, reply_markup=keyboard)


def _parse_decimal(
    raw: str,
    field: str,
    language: str = DEFAULT_LANGUAGE,
    *,
    allow_zero: bool,
) -> Decimal | str:
    translated_field = field_name(field, language) if field in {"quantity", "unit_cost", "sale_price"} else field
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return translated_text("invalid_number", language, field=translated_field)
    if not value.is_finite() or value < 0 or (value == 0 and not allow_zero):
        comparison = translated_text("zero_or_more" if allow_zero else "greater_zero", language)
        return translated_text("number_range", language, field=translated_field, comparison=comparison)
    return value


def _parse_iso_date(raw: str, language: str = DEFAULT_LANGUAGE) -> date | str:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return translated_text("invalid_date", language)


def _parse_date_or_today(raw: str, language: str = DEFAULT_LANGUAGE) -> date | str:
    return date.today() if matches_button(raw, "today") else _parse_iso_date(raw, language)

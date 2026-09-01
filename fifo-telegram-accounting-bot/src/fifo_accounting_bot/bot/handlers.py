from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from telegram import Update
from telegram.error import NetworkError
from telegram.ext import Application, CommandHandler, ContextTypes

from fifo_accounting_bot.bot.formatters import format_report, format_sale, format_stock, money, quantity
from fifo_accounting_bot.bot.parsers import (
    command_payload,
    parse_add_product,
    parse_purchase,
    parse_report,
    parse_sale,
    parse_stock,
)
from fifo_accounting_bot.exceptions import AccountingError
from fifo_accounting_bot.services import InventoryService

LOGGER = logging.getLogger(__name__)

HELP_TEXT = """FIFO Accounting Bot

Each Telegram user has a separate inventory.

Commands:
/addproduct SKU | Product name | unit
/purchase SKU QUANTITY UNIT_COST [YYYY-MM-DD]
/sale SKU QUANTITY [UNIT_PRICE] [YYYY-MM-DD]
/stock [SKU]
/report [START_DATE END_DATE]
/help

Examples:
/addproduct COFFEE-1 | Arabica beans | kg
/purchase COFFEE-1 10 8.50 2026-08-01
/purchase COFFEE-1 5 9.25 2026-08-10
/sale COFFEE-1 12 14.00 2026-08-20

Dates use YYYY-MM-DD. Amounts use a dot as the decimal separator. The sale price is optional; FIFO COGS is always calculated."""


class InventoryHandlers:
    """Telegram command adapter. Register another handler module for a future service."""

    def __init__(
        self,
        service: InventoryService,
        allowed_user_ids: frozenset[int] = frozenset(),
    ) -> None:
        self._service = service
        self._allowed_user_ids = allowed_user_ids

    def register(self, application: Application) -> None:
        application.add_handler(CommandHandler(["start", "help"], self.start))
        application.add_handler(CommandHandler("addproduct", self.add_product))
        application.add_handler(CommandHandler("purchase", self.purchase))
        application.add_handler(CommandHandler("sale", self.sale))
        application.add_handler(CommandHandler("stock", self.stock))
        application.add_handler(CommandHandler("report", self.report))

    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._authorize(update):
            return
        await self._reply(update, HELP_TEXT)

    async def add_product(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._run_command(update, self._add_product)

    async def purchase(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._run_command(update, self._purchase)

    async def sale(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._run_command(update, self._sale)

    async def stock(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._run_command(update, self._stock)

    async def report(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._run_command(update, self._report)

    async def _add_product(self, update: Update, owner_id: int) -> str:
        command = parse_add_product(command_payload(update.effective_message.text))
        result = await asyncio.to_thread(
            self._service.add_product,
            owner_id,
            command.sku,
            command.name,
            command.unit,
        )
        return f"Product added: {result.sku} — {result.name} ({result.unit})"

    async def _purchase(self, update: Update, owner_id: int) -> str:
        command = parse_purchase(command_payload(update.effective_message.text))
        result = await asyncio.to_thread(
            self._service.record_purchase,
            owner_id,
            command.sku,
            command.quantity,
            command.unit_cost,
            command.purchased_on,
        )
        return (
            f"Purchase batch #{result.batch_id} recorded for {result.sku}\n"
            f"{quantity(result.quantity)} × {money(result.unit_cost)} = {money(result.total_cost)}\n"
            f"Date: {result.purchased_on.isoformat()}"
        )

    async def _sale(self, update: Update, owner_id: int) -> str:
        command = parse_sale(command_payload(update.effective_message.text))
        result = await asyncio.to_thread(
            self._service.record_sale,
            owner_id,
            command.sku,
            command.quantity,
            command.unit_sale_price,
            command.sold_on,
        )
        return format_sale(result)

    async def _stock(self, update: Update, owner_id: int) -> str:
        sku = parse_stock(command_payload(update.effective_message.text))
        lines = await asyncio.to_thread(self._service.get_stock, owner_id, sku)
        return format_stock(lines)

    async def _report(self, update: Update, owner_id: int) -> str:
        period_start, period_end = parse_report(
            command_payload(update.effective_message.text)
        )
        report = await asyncio.to_thread(
            self._service.get_report, owner_id, period_start, period_end
        )
        return format_report(report)

    async def _run_command(
        self,
        update: Update,
        command: Callable[[Update, int], Awaitable[str]],
    ) -> None:
        owner_id = await self._authorize(update)
        if owner_id is None:
            return
        try:
            response = await command(update, owner_id)
        except AccountingError as exc:
            await self._reply(update, f"Could not complete that command: {exc}")
            return
        await self._reply(update, response)

    async def _authorize(self, update: Update) -> int | None:
        user = update.effective_user
        if user is None:
            await self._reply(update, "This command must be sent by a Telegram user.")
            return None
        if self._allowed_user_ids and user.id not in self._allowed_user_ids:
            LOGGER.warning("Rejected Telegram user ID %s", user.id)
            await self._reply(update, "This bot is private and your account is not authorized.")
            return None
        return user.id

    @staticmethod
    async def _reply(update: Update, text: str) -> None:
        message = update.effective_message
        if message is not None:
            await message.reply_text(text)


async def log_unhandled_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    if isinstance(error, NetworkError):
        LOGGER.warning("Temporary Telegram network error; polling will retry: %s", error)
        return
    if error is not None:
        LOGGER.error(
            "Unhandled error while processing Telegram update",
            exc_info=(type(error), error, error.__traceback__),
        )
    else:
        LOGGER.error("Unhandled error while processing Telegram update")
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "An unexpected error occurred. Check 📦 Stock before retrying the action."
        )

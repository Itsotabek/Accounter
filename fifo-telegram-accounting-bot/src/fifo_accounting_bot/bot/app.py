from __future__ import annotations

from telegram import BotCommand
from telegram.ext import Application

from fifo_accounting_bot.bot.accounting_menu import AccountingMenuHandlers
from fifo_accounting_bot.bot.handlers import InventoryHandlers, log_unhandled_error
from fifo_accounting_bot.bot.menu import GuidedMenuHandlers
from fifo_accounting_bot.config import Settings
from fifo_accounting_bot.services import AccountingService, InventoryService, UserService
from fifo_accounting_bot.services.ai_helper import AIConfig, AIHelper


async def _set_bot_commands(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Open the Accounter menu"),
            BotCommand("addproduct", "Add a product"),
            BotCommand("purchase", "Record a purchase batch"),
            BotCommand("sale", "Record a FIFO sale"),
            BotCommand("stock", "Show current FIFO inventory"),
            BotCommand("report", "Show sales, COGS, profit, and stock"),
            BotCommand("help", "Show command examples"),
        ]
    )


def create_application(settings: Settings, inventory_service: InventoryService) -> Application:
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(_set_bot_commands)
        .build()
    )
    users = UserService(inventory_service.session_factory)
    accounting = AccountingService(inventory_service.session_factory)
    ai = AIHelper(
        AIConfig(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            max_output_tokens=settings.ai_max_output_tokens,
        )
    )
    AccountingMenuHandlers(
        accounting,
        inventory_service,
        users,
        settings,
        settings.allowed_telegram_user_ids,
    ).register(application)
    GuidedMenuHandlers(
        inventory_service,
        users,
        ai,
        settings,
        settings.allowed_telegram_user_ids,
    ).register(application)
    InventoryHandlers(
        inventory_service, settings.allowed_telegram_user_ids
    ).register(application)
    application.add_error_handler(log_unhandled_error)
    return application

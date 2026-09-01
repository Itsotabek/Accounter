from __future__ import annotations

import asyncio
from datetime import date
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

from telegram import Chat, Message, Update, User
from telegram.ext import ConversationHandler

from fifo_accounting_bot.bot.app import create_application
from fifo_accounting_bot.bot.menu import (
    ADD_PRODUCT,
    ADD_SKU,
    BACK_TO_MENU,
    BANKING,
    CANCEL,
    CONTACTS,
    DASHBOARD,
    FINANCIAL_REPORTS,
    GuidedMenuHandlers,
    LANGUAGE_SELECT,
    MAIN_KEYBOARD,
    MONEY_IN,
    MONEY_OUT,
    PURCHASE,
    SETTINGS,
    SMART_IMPORT,
    START_OVER,
    TODAY,
    _parse_date_or_today,
    _parse_decimal,
    _parse_iso_date,
)
from fifo_accounting_bot.bot.i18n import button_values
from fifo_accounting_bot.config import Settings
from fifo_accounting_bot.services.ai_helper import AIConfig, AIHelper
from fifo_accounting_bot.services.users import UserService


def test_main_keyboard_exposes_common_actions():
    labels = [button.text for row in MAIN_KEYBOARD.keyboard for button in row]
    assert DASHBOARD in labels
    assert MONEY_IN in labels
    assert MONEY_OUT in labels
    assert BANKING in labels
    assert CONTACTS in labels
    assert FINANCIAL_REPORTS in labels
    assert SMART_IMPORT in labels
    assert SETTINGS in labels
    assert len(labels) == 11


def test_guided_menu_is_registered_before_legacy_commands(inventory):
    service, _ = inventory
    application = create_application(Settings("123456:TEST_TOKEN"), service)

    conversations = [
        handler
        for handler in application.handlers[0]
        if isinstance(handler, ConversationHandler)
    ]
    assert {handler.name for handler in conversations[:2]} == {
        "general_accounting_assistant",
        "guided_fifo_assistant",
    }


def test_menu_decimal_validation():
    assert _parse_decimal("2.5", "Quantity", allow_zero=False) == Decimal("2.5")
    assert isinstance(_parse_decimal("0", "Quantity", allow_zero=False), str)
    assert isinstance(_parse_decimal("NaN", "Quantity", allow_zero=False), str)


def test_menu_date_validation():
    assert _parse_iso_date("2026-08-31") == date(2026, 8, 31)
    assert isinstance(_parse_iso_date("31-08-2026"), str)
    assert _parse_date_or_today(TODAY) == date.today()


def test_control_buttons_are_never_consumed_as_form_data(inventory):
    service, _ = inventory
    application = create_application(Settings("123456:TEST_TOKEN"), service)
    conversation = _guided_conversation(application)

    for label in button_values("cancel") + button_values("main_menu"):
        update = _text_update(label)
        assert all(
            not any(handler.check_update(update) for handler in handlers)
            for handlers in conversation.states.values()
        )
        assert any(handler.check_update(update) for handler in conversation.fallbacks)


def test_start_over_is_routed_in_every_conversation_state(inventory):
    service, _ = inventory
    application = create_application(Settings("123456:TEST_TOKEN"), service)
    conversation = _guided_conversation(application)
    for label in button_values("start_over"):
        update = _text_update(label)
        assert all(
            any(handler.check_update(update) for handler in handlers)
            for handlers in conversation.states.values()
        )


def test_stale_control_keyboard_recovers_after_process_restart(inventory):
    service, _ = inventory
    application = create_application(Settings("123456:TEST_TOKEN"), service)
    conversation = _guided_conversation(application)

    labels = (
        button_values("cancel")
        + button_values("main_menu")
        + button_values("start_over")
    )
    for label in labels:
        update = _text_update(label)
        assert any(
            handler.check_update(update) for handler in conversation.entry_points
        )


def test_start_over_resets_the_current_draft(inventory):
    service, session_factory = inventory
    settings = Settings("123456:TEST_TOKEN")
    menu = GuidedMenuHandlers(
        service,
        UserService(session_factory),
        AIHelper(AIConfig("", "test-model")),
        settings,
    )
    menu._reply = AsyncMock()
    context = type("Context", (), {})()
    context.user_data = {
        "guided_draft": {"operation": "add_product", "sku": "WRONG"}
    }

    state = asyncio.run(menu.restart(_text_update(START_OVER), context))

    assert state == ADD_SKU
    assert context.user_data["guided_draft"] == {"operation": "add_product"}
    menu._reply.assert_awaited_once()


def test_owner_button_is_hidden_from_users_and_visible_to_owner(inventory):
    service, session_factory = inventory
    owner_id = 99
    settings = Settings(
        "123456:TEST_TOKEN", owner_telegram_user_ids=frozenset({owner_id})
    )
    menu = GuidedMenuHandlers(
        service,
        UserService(session_factory),
        AIHelper(AIConfig("", "test-model")),
        settings,
    )

    user_labels = [item.text for row in menu._main_keyboard("en", 100).keyboard for item in row]
    owner_labels = [item.text for row in menu._main_keyboard("en", owner_id).keyboard for item in row]

    assert "🛡 Owner panel" not in user_labels
    assert "🛡 Owner panel" in owner_labels


def test_every_supported_language_has_complete_button_labels():
    from fifo_accounting_bot.bot.i18n import BUTTONS, LANGUAGES

    assert all(set(values) == set(LANGUAGES) for values in BUTTONS.values())


def test_first_start_requests_and_persists_language(inventory):
    service, session_factory = inventory
    users = UserService(session_factory)
    settings = Settings("123456:TEST_TOKEN")
    menu = GuidedMenuHandlers(
        service,
        users,
        AIHelper(AIConfig("", "test-model")),
        settings,
    )
    menu._reply = AsyncMock()
    context = type("Context", (), {})()
    context.user_data = {}

    state = asyncio.run(menu.show_menu(_text_update("/start"), context))
    assert state == LANGUAGE_SELECT
    assert users.get(99).language is None

    state = asyncio.run(menu.select_language(_text_update("🇮🇹 Italiano"), context))
    assert state == ConversationHandler.END
    assert users.get(99).language == "it"


def test_settings_renders_language_and_owner_role(inventory):
    service, session_factory = inventory
    users = UserService(session_factory)
    users.touch(99, "tester", "Test User")
    users.set_language(99, "it")
    settings = Settings(
        "123456:TEST_TOKEN", owner_telegram_user_ids=frozenset({99})
    )
    menu = GuidedMenuHandlers(
        service,
        users,
        AIHelper(AIConfig("", "test-model")),
        settings,
    )
    menu._reply = AsyncMock()
    context = type("Context", (), {})()
    context.user_data = {}

    state = asyncio.run(menu.show_settings(_text_update("⚙️ Impostazioni"), context))

    assert state == ConversationHandler.END
    rendered = menu._reply.await_args.args[1]
    assert "Ruolo: Proprietario" in rendered
    assert "Lingua: Italiano" in rendered


def _text_update(text: str) -> Update:
    user = User(id=99, first_name="Test", is_bot=False)
    chat = Chat(id=99, type="private")
    message = Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=chat,
        from_user=user,
        text=text,
    )
    return Update(update_id=1, message=message)


def _guided_conversation(application):
    return next(
        handler
        for handler in application.handlers[0]
        if isinstance(handler, ConversationHandler)
        and handler.name == "guided_fifo_assistant"
    )

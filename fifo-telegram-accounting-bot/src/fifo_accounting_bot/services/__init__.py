"""Accounting service layer.

Telegram handlers call these services, but the services have no Telegram dependency.
Future accounting modules can follow the same boundary.
"""

from fifo_accounting_bot.services.accounting import AccountingService
from fifo_accounting_bot.services.inventory import InventoryService
from fifo_accounting_bot.services.users import UserService

__all__ = ["AccountingService", "InventoryService", "UserService"]

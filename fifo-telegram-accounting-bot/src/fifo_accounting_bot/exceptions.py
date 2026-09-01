class AccountingError(Exception):
    """Base error that is safe to present to a bot user."""


class ValidationError(AccountingError):
    """Input or business-rule validation failed."""


class NotFoundError(AccountingError):
    """A requested accounting entity does not exist."""


class DuplicateError(AccountingError):
    """An entity conflicts with an existing record."""


class InsufficientStockError(AccountingError):
    """A sale requests more stock than is currently available."""

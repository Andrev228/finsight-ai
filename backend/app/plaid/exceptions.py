"""Plaid integration errors."""


class PlaidConfigurationError(RuntimeError):
    """Raised when Plaid credentials are not configured."""


class PlaidApiError(RuntimeError):
    """Raised when Plaid rejects a request or cannot be reached."""

    def __init__(self, error_code: str, request_id: str | None = None) -> None:
        super().__init__(error_code)
        self.error_code = error_code
        self.request_id = request_id


class PlaidItemAlreadyExistsError(RuntimeError):
    """Raised when a Plaid Item has already been connected."""

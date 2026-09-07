"""Errors raised by the LLM gateway."""


class LLMConfigurationError(RuntimeError):
    """Raised when the LLM provider is not configured."""


class LLMProviderError(RuntimeError):
    """Raised when the LLM provider rejects or fails a request."""

    def __init__(
        self,
        error_code: str,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(error_code)
        self.error_code = error_code
        self.status_code = status_code
        self.request_id = request_id

"""Custom exceptions for LLM module."""


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM provider configuration is invalid."""

    pass


class LLMConnectionError(LLMError):
    """Raised when connection to LLM provider fails."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM provider rate limit is exceeded."""

    pass


class LLMAuthenticationError(LLMError):
    """Raised when LLM provider authentication fails."""

    pass

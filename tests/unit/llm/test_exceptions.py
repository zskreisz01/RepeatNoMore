"""Unit tests for LLM exceptions."""

import pytest
from app.llm.exceptions import (
    LLMError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMAuthenticationError,
)


class TestLLMError:
    """Test cases for base LLMError."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = LLMError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)

    def test_error_inheritance(self):
        """Test that LLMError inherits from Exception."""
        error = LLMError("Test")
        assert isinstance(error, Exception)

    def test_error_with_cause(self):
        """Test error with underlying cause."""
        cause = ValueError("Original error")
        error = LLMError("Wrapped error")
        error.__cause__ = cause

        assert error.__cause__ is cause


class TestLLMConfigurationError:
    """Test cases for LLMConfigurationError."""

    def test_configuration_error(self):
        """Test configuration error creation."""
        error = LLMConfigurationError("Missing API key")
        assert str(error) == "Missing API key"

    def test_inherits_from_llm_error(self):
        """Test that it inherits from LLMError."""
        error = LLMConfigurationError("Test")
        assert isinstance(error, LLMError)
        assert isinstance(error, Exception)


class TestLLMConnectionError:
    """Test cases for LLMConnectionError."""

    def test_connection_error(self):
        """Test connection error creation."""
        error = LLMConnectionError("Failed to connect to Ollama")
        assert str(error) == "Failed to connect to Ollama"

    def test_inherits_from_llm_error(self):
        """Test that it inherits from LLMError."""
        error = LLMConnectionError("Test")
        assert isinstance(error, LLMError)


class TestLLMRateLimitError:
    """Test cases for LLMRateLimitError."""

    def test_rate_limit_error(self):
        """Test rate limit error creation."""
        error = LLMRateLimitError("Too many requests")
        assert str(error) == "Too many requests"

    def test_inherits_from_llm_error(self):
        """Test that it inherits from LLMError."""
        error = LLMRateLimitError("Test")
        assert isinstance(error, LLMError)


class TestLLMAuthenticationError:
    """Test cases for LLMAuthenticationError."""

    def test_authentication_error(self):
        """Test authentication error creation."""
        error = LLMAuthenticationError("Invalid API key")
        assert str(error) == "Invalid API key"

    def test_inherits_from_llm_error(self):
        """Test that it inherits from LLMError."""
        error = LLMAuthenticationError("Test")
        assert isinstance(error, LLMError)


class TestExceptionHierarchy:
    """Test the exception hierarchy."""

    def test_all_errors_inherit_from_llm_error(self):
        """Test that all specific errors inherit from LLMError."""
        errors = [
            LLMConfigurationError("test"),
            LLMConnectionError("test"),
            LLMRateLimitError("test"),
            LLMAuthenticationError("test"),
        ]

        for error in errors:
            assert isinstance(error, LLMError)

    def test_can_catch_all_with_base_class(self):
        """Test that all errors can be caught with LLMError."""
        error_classes = [
            LLMConfigurationError,
            LLMConnectionError,
            LLMRateLimitError,
            LLMAuthenticationError,
        ]

        for error_class in error_classes:
            try:
                raise error_class("test error")
            except LLMError as e:
                assert "test error" in str(e)
            except Exception:
                pytest.fail(f"{error_class.__name__} was not caught by LLMError")

"""Unit tests for LLM base provider."""

import pytest
from unittest.mock import Mock, patch
from app.llm.base import BaseLLMProvider
from app.llm.types import LLMMessage, LLMOptions, LLMResponse, LLMProviderType, TokenUsage
from app.llm.exceptions import LLMError


class ConcreteProvider(BaseLLMProvider):
    """Concrete implementation for testing abstract base class."""

    @property
    def provider_name(self) -> str:
        return "test"

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OLLAMA

    def _do_chat(self, messages, options):
        return LLMResponse(
            content="Test response",
            model=self.model,
            provider=self.provider_type,
            tokens=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            duration=0.5
        )

    def is_available(self) -> bool:
        return True

    def list_models(self):
        return ["model-1", "model-2"]


class FailingProvider(BaseLLMProvider):
    """Provider that raises errors for testing."""

    @property
    def provider_name(self) -> str:
        return "failing"

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OLLAMA

    def _do_chat(self, messages, options):
        raise Exception("Test error")

    def is_available(self) -> bool:
        return False

    def list_models(self):
        return []


class TestBaseLLMProvider:
    """Test cases for BaseLLMProvider."""

    @pytest.fixture
    def provider(self):
        """Create a concrete provider for testing."""
        return ConcreteProvider(model="test-model")

    @pytest.fixture
    def failing_provider(self):
        """Create a failing provider for testing."""
        return FailingProvider(model="fail-model")

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.model == "test-model"
        assert provider.model_name == "test-model"
        assert provider.provider_name == "test"

    def test_initialization_with_config(self):
        """Test provider initialization with extra config."""
        provider = ConcreteProvider(
            model="test-model",
            api_key="test-key",
            custom_option="value"
        )
        assert provider.model == "test-model"

    def test_chat_returns_response(self, provider):
        """Test that chat returns LLMResponse."""
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.provider == LLMProviderType.OLLAMA

    def test_chat_with_options(self, provider):
        """Test chat with custom options."""
        messages = [LLMMessage(role="user", content="Hello")]
        options = LLMOptions(temperature=0.5, max_tokens=100)

        response = provider.chat(messages, options)

        assert isinstance(response, LLMResponse)

    def test_chat_uses_default_options(self, provider):
        """Test chat uses default options when none provided."""
        messages = [LLMMessage(role="user", content="Hello")]

        response = provider.chat(messages)

        assert isinstance(response, LLMResponse)

    def test_chat_error_handling(self, failing_provider):
        """Test that chat wraps errors in LLMError."""
        messages = [LLMMessage(role="user", content="Hello")]

        with pytest.raises(LLMError) as exc_info:
            failing_provider.chat(messages)

        assert "Test error" in str(exc_info.value)

    def test_is_available(self, provider):
        """Test is_available returns correct value."""
        assert provider.is_available() is True

    def test_is_not_available(self, failing_provider):
        """Test is_available returns False for failing provider."""
        assert failing_provider.is_available() is False

    def test_list_models(self, provider):
        """Test list_models returns model list."""
        models = provider.list_models()
        assert models == ["model-1", "model-2"]

    def test_model_name_property(self, provider):
        """Test model_name property returns correct value."""
        assert provider.model_name == "test-model"

    def test_provider_name_property(self, provider):
        """Test provider_name property returns correct value."""
        assert provider.provider_name == "test"

    def test_chat_measures_duration(self, provider):
        """Test that chat response includes duration."""
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert response.duration is not None
        assert response.duration >= 0



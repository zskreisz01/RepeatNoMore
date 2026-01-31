"""Unit tests for LLM providers."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.llm.types import LLMMessage, LLMOptions, LLMResponse, LLMProviderType, TokenUsage
from app.llm.providers.ollama import OllamaProvider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.cursor import CursorProvider
from app.llm.exceptions import LLMError, LLMConfigurationError


class TestOllamaProvider:
    """Test cases for OllamaProvider."""

    @pytest.fixture
    def provider(self):
        """Create Ollama provider for testing."""
        return OllamaProvider(
            model="llama3.2:3b",
            host="localhost",
            port=11434
        )

    def test_initialization(self, provider):
        """Test provider initialization."""
        assert provider.model == "llama3.2:3b"
        assert provider.provider_name == "ollama"
        assert provider.provider_type == LLMProviderType.OLLAMA

    def test_initialization_with_custom_host(self):
        """Test provider with custom host."""
        provider = OllamaProvider(
            model="test",
            host="custom-host",
            port=12345
        )
        assert provider.host == "custom-host"
        assert provider.port == 12345

    def test_chat_success(self, provider):
        """Test successful chat completion."""
        mock_response = {
            "message": {"content": "Hello! How can I help you?"},
            "model": "llama3.2:3b",
            "eval_count": 50,
            "prompt_eval_count": 10,
            "total_duration": 1000000000,  # 1 second in nanoseconds
        }

        with patch("app.llm.providers.ollama.ollama") as mock_ollama:
            mock_ollama.chat.return_value = mock_response

            messages = [LLMMessage(role="user", content="Hello")]
            response = provider.chat(messages)

        assert isinstance(response, LLMResponse)
        assert response.content == "Hello! How can I help you?"
        assert response.model == "llama3.2:3b"
        assert response.provider == LLMProviderType.OLLAMA

    def test_chat_with_options(self, provider):
        """Test chat with custom options."""
        mock_response = {
            "message": {"content": "Response"},
            "model": "llama3.2:3b",
            "eval_count": 20,
            "prompt_eval_count": 5,
            "total_duration": 500000000,
        }

        with patch("app.llm.providers.ollama.ollama") as mock_ollama:
            mock_ollama.chat.return_value = mock_response

            messages = [LLMMessage(role="user", content="Test")]
            options = LLMOptions(temperature=0.3, max_tokens=100)
            response = provider.chat(messages, options)

            # Verify options were passed correctly
            call_kwargs = mock_ollama.chat.call_args[1]
            assert call_kwargs["options"]["temperature"] == 0.3
            assert call_kwargs["options"]["num_predict"] == 100

    def test_is_available_true(self, provider):
        """Test is_available when Ollama is running."""
        with patch("app.llm.providers.ollama.ollama") as mock_ollama:
            mock_ollama.list.return_value = {"models": []}
            assert provider.is_available() is True

    def test_is_available_false(self, provider):
        """Test is_available when Ollama is not running."""
        with patch("app.llm.providers.ollama.ollama") as mock_ollama:
            mock_ollama.list.side_effect = Exception("Connection refused")
            assert provider.is_available() is False

    def test_list_models(self, provider):
        """Test listing available models."""
        with patch("app.llm.providers.ollama.ollama") as mock_ollama:
            mock_ollama.list.return_value = {
                "models": [
                    {"name": "llama3.2:3b"},
                    {"name": "mistral:7b"}
                ]
            }
            models = provider.list_models()

        assert "llama3.2:3b" in models
        assert "mistral:7b" in models

    def test_convert_messages(self, provider):
        """Test message conversion for Ollama."""
        messages = [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hello"),
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 2
        assert converted[0]["role"] == "system"
        assert converted[0]["content"] == "You are helpful."
        assert converted[1]["role"] == "user"


class TestAnthropicProvider:
    """Test cases for AnthropicProvider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = AnthropicProvider(
            model="claude-sonnet-4-20250514",
            api_key="test-key"
        )
        assert provider.model == "claude-sonnet-4-20250514"
        assert provider.provider_name == "anthropic"
        assert provider.provider_type == LLMProviderType.ANTHROPIC
        assert provider.api_key == "test-key"

    def test_initialization_without_api_key_raises_error(self):
        """Test that missing API key raises error."""
        with pytest.raises(LLMConfigurationError) as exc_info:
            AnthropicProvider(model="test", api_key="")

        assert "API key" in str(exc_info.value)

    def test_list_models(self):
        """Test listing available models."""
        provider = AnthropicProvider(model="test", api_key="key")
        models = provider.list_models()
        assert "claude-sonnet-4-20250514" in models
        assert "claude-3-5-sonnet-20241022" in models

    def test_convert_messages(self):
        """Test message conversion for Anthropic."""
        provider = AnthropicProvider(model="test", api_key="key")
        messages = [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hello"),
        ]

        system_msg, chat_msgs = provider._convert_messages(messages)

        assert system_msg == "You are helpful."
        assert len(chat_msgs) == 1
        assert chat_msgs[0]["role"] == "user"
        assert chat_msgs[0]["content"] == "Hello"


class TestOpenAIProvider:
    """Test cases for OpenAIProvider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = OpenAIProvider(
            model="gpt-4-turbo-preview",
            api_key="test-key"
        )
        assert provider.model == "gpt-4-turbo-preview"
        assert provider.provider_name == "openai"
        assert provider.provider_type == LLMProviderType.OPENAI
        assert provider.api_key == "test-key"

    def test_initialization_without_api_key_raises_error(self):
        """Test that missing API key raises error."""
        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenAIProvider(model="test", api_key="")

        assert "API key" in str(exc_info.value)

    def test_initialization_with_custom_base_url(self):
        """Test provider with custom base URL."""
        provider = OpenAIProvider(
            model="test",
            api_key="key",
            base_url="https://custom.openai.azure.com"
        )
        assert provider.base_url == "https://custom.openai.azure.com"

    def test_convert_messages(self):
        """Test message conversion for OpenAI."""
        provider = OpenAIProvider(model="test", api_key="key")
        messages = [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hello"),
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 2
        assert converted[0]["role"] == "system"
        assert converted[0]["content"] == "You are helpful."
        assert converted[1]["role"] == "user"

    def test_list_models_fallback(self):
        """Test listing models returns fallback list."""
        provider = OpenAIProvider(model="test", api_key="key")
        models = provider.list_models()
        assert "gpt-4-turbo-preview" in models
        assert "gpt-4" in models


class TestCursorProvider:
    """Test cases for CursorProvider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = CursorProvider(
            model="cursor-small",
            api_key="test-key"
        )
        assert provider.model == "cursor-small"
        assert provider.provider_name == "cursor"
        assert provider.provider_type == LLMProviderType.CURSOR
        assert provider.api_key == "test-key"

    def test_initialization_without_api_key_raises_error(self):
        """Test that missing API key raises error."""
        with pytest.raises(LLMConfigurationError) as exc_info:
            CursorProvider(model="test", api_key="")

        assert "API key" in str(exc_info.value)

    def test_default_base_url(self):
        """Test that default base URL is Cursor's API."""
        provider = CursorProvider(model="test", api_key="key")
        assert provider.base_url == "https://api.cursor.sh/v1"

    def test_custom_base_url(self):
        """Test provider with custom base URL."""
        provider = CursorProvider(
            model="test",
            api_key="key",
            base_url="https://custom.cursor.api"
        )
        assert provider.base_url == "https://custom.cursor.api"

    def test_list_models(self):
        """Test listing available models."""
        provider = CursorProvider(model="test", api_key="key")
        models = provider.list_models()
        assert "cursor-small" in models
        assert "cursor-large" in models

    def test_convert_messages(self):
        """Test message conversion for Cursor."""
        provider = CursorProvider(model="test", api_key="key")
        messages = [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hello"),
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 2
        assert converted[0]["role"] == "system"
        assert converted[0]["content"] == "You are helpful."


class TestProviderTokenUsage:
    """Test cases for token usage tracking with Ollama provider."""

    def test_ollama_token_usage(self):
        """Test token usage from Ollama response."""
        provider = OllamaProvider(model="test", host="localhost", port=11434)

        mock_response = {
            "message": {"content": "Response"},
            "model": "test",
            "eval_count": 50,
            "prompt_eval_count": 10,
            "total_duration": 1000000000,
        }

        with patch("app.llm.providers.ollama.ollama") as mock_ollama:
            mock_ollama.chat.return_value = mock_response

            messages = [LLMMessage(role="user", content="Test")]
            response = provider.chat(messages)

        assert response.tokens is not None
        assert response.tokens.completion_tokens == 50
        assert response.tokens.prompt_tokens == 10
        assert response.tokens.total_tokens == 60

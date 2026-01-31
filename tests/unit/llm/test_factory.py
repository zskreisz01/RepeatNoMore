"""Unit tests for LLM provider factory."""

import pytest
from unittest.mock import patch, MagicMock

from app.llm.factory import LLMProviderFactory, get_llm_provider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.cursor import CursorProvider
from app.llm.exceptions import LLMConfigurationError


class TestLLMProviderFactory:
    """Test cases for LLMProviderFactory."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear provider cache before each test."""
        LLMProviderFactory.clear_cache()
        yield
        LLMProviderFactory.clear_cache()

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider."""
        provider = LLMProviderFactory.create(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key="test-key"
        )

        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-sonnet-4-20250514"

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = LLMProviderFactory.create(
            provider="openai",
            model="gpt-4-turbo-preview",
            api_key="test-key"
        )

        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-4-turbo-preview"

    def test_create_cursor_provider(self):
        """Test creating Cursor provider."""
        provider = LLMProviderFactory.create(
            provider="cursor",
            model="cursor-small",
            api_key="test-key"
        )

        assert isinstance(provider, CursorProvider)
        assert provider.model == "cursor-small"

    def test_create_unknown_provider_raises_error(self):
        """Test that unknown provider type raises error."""
        with pytest.raises(LLMConfigurationError) as exc_info:
            LLMProviderFactory.create(
                provider="unknown",
                model="test"
            )

        assert "Unknown provider" in str(exc_info.value)

    def test_create_with_case_insensitive_type(self):
        """Test that provider type is case-insensitive."""
        provider = LLMProviderFactory.create(
            provider="ANTHROPIC",
            model="test",
            api_key="key"
        )
        assert isinstance(provider, AnthropicProvider)

        provider = LLMProviderFactory.create(
            provider="OpenAI",
            model="test",
            api_key="key"
        )
        assert isinstance(provider, OpenAIProvider)

    def test_list_providers(self):
        """Test listing available providers."""
        providers = LLMProviderFactory.list_providers()

        assert "anthropic" in providers
        assert "openai" in providers
        assert "cursor" in providers
        # Note: Ollama has been removed as a supported provider


class TestGetLLMProvider:
    """Test cases for get_llm_provider convenience function."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear provider cache before each test."""
        LLMProviderFactory.clear_cache()
        yield
        LLMProviderFactory.clear_cache()

    def test_get_provider_from_settings(self):
        """Test getting provider from settings."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.anthropic_max_tokens = 4096

        with patch("app.config.get_settings", return_value=mock_settings):
            provider = get_llm_provider()

        assert isinstance(provider, AnthropicProvider)

    def test_get_anthropic_provider_from_settings(self):
        """Test getting Anthropic provider from settings."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.anthropic_max_tokens = 4096

        with patch("app.config.get_settings", return_value=mock_settings):
            provider = get_llm_provider()

        assert isinstance(provider, AnthropicProvider)

    def test_get_openai_provider_from_settings(self):
        """Test getting OpenAI provider from settings."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        mock_settings.openai_model = "gpt-4-turbo-preview"
        mock_settings.openai_base_url = ""

        with patch("app.config.get_settings", return_value=mock_settings):
            provider = get_llm_provider()

        assert isinstance(provider, OpenAIProvider)

    def test_get_cursor_provider_from_settings(self):
        """Test getting Cursor provider from settings."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "cursor"
        mock_settings.cursor_api_key = "test-key"
        mock_settings.cursor_model = "cursor-small"
        mock_settings.cursor_base_url = "https://api.cursor.sh/v1"

        with patch("app.config.get_settings", return_value=mock_settings):
            provider = get_llm_provider()

        assert isinstance(provider, CursorProvider)

    def test_provider_caching(self):
        """Test that providers are cached."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.anthropic_max_tokens = 4096

        with patch("app.config.get_settings", return_value=mock_settings):
            provider1 = get_llm_provider()
            provider2 = get_llm_provider()

        assert provider1 is provider2

    def test_override_provider_type(self):
        """Test overriding provider type."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.anthropic_max_tokens = 4096
        mock_settings.openai_api_key = "test-openai-key"
        mock_settings.openai_model = "gpt-4-turbo-preview"
        mock_settings.openai_base_url = ""

        with patch("app.config.get_settings", return_value=mock_settings):
            provider = get_llm_provider(provider="openai")

        assert isinstance(provider, OpenAIProvider)

    def test_override_model(self):
        """Test overriding model."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.anthropic_model = "default-model"
        mock_settings.anthropic_max_tokens = 4096

        with patch("app.config.get_settings", return_value=mock_settings):
            provider = get_llm_provider(model="custom-model")

        assert provider.model == "custom-model"

    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises error for cloud providers."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "anthropic"
        mock_settings.anthropic_api_key = ""
        mock_settings.anthropic_model = "claude-sonnet-4-20250514"
        mock_settings.anthropic_max_tokens = 4096

        with patch("app.config.get_settings", return_value=mock_settings):
            with pytest.raises(LLMConfigurationError) as exc_info:
                get_llm_provider()

        assert "api key" in str(exc_info.value).lower()

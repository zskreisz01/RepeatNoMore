"""Unit tests for LLM types."""

import pytest
from app.llm.types import (
    LLMProviderType,
    LLMMessage,
    LLMOptions,
    TokenUsage,
    LLMResponse,
)


class TestLLMProviderType:
    """Test cases for LLMProviderType enum."""

    def test_provider_values(self):
        """Test that all provider types have correct values."""
        assert LLMProviderType.OLLAMA.value == "ollama"
        assert LLMProviderType.ANTHROPIC.value == "anthropic"
        assert LLMProviderType.OPENAI.value == "openai"
        assert LLMProviderType.CURSOR.value == "cursor"

    def test_all_providers_defined(self):
        """Test that all expected providers are defined."""
        providers = [p.value for p in LLMProviderType]
        assert "ollama" in providers
        assert "anthropic" in providers
        assert "openai" in providers
        assert "cursor" in providers
        assert len(providers) == 4


class TestLLMMessage:
    """Test cases for LLMMessage dataclass."""

    def test_create_user_message(self):
        """Test creating a user message."""
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_create_system_message(self):
        """Test creating a system message."""
        msg = LLMMessage(role="system", content="You are helpful.")
        assert msg.role == "system"
        assert msg.content == "You are helpful."

    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        msg = LLMMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"
        assert msg.content == "Hi there!"

    def test_message_equality(self):
        """Test message equality comparison."""
        msg1 = LLMMessage(role="user", content="test")
        msg2 = LLMMessage(role="user", content="test")
        assert msg1 == msg2

    def test_message_inequality(self):
        """Test message inequality."""
        msg1 = LLMMessage(role="user", content="test1")
        msg2 = LLMMessage(role="user", content="test2")
        assert msg1 != msg2


class TestLLMOptions:
    """Test cases for LLMOptions dataclass."""

    def test_default_values(self):
        """Test default option values."""
        opts = LLMOptions()
        assert opts.temperature == 0.7
        assert opts.max_tokens == 2000
        assert opts.top_p is None
        assert opts.stop_sequences is None

    def test_custom_temperature(self):
        """Test setting custom temperature."""
        opts = LLMOptions(temperature=0.3)
        assert opts.temperature == 0.3

    def test_custom_max_tokens(self):
        """Test setting custom max_tokens."""
        opts = LLMOptions(max_tokens=500)
        assert opts.max_tokens == 500

    def test_custom_top_p(self):
        """Test setting custom top_p."""
        opts = LLMOptions(top_p=0.9)
        assert opts.top_p == 0.9

    def test_custom_stop_sequences(self):
        """Test setting custom stop sequences."""
        opts = LLMOptions(stop_sequences=["END", "STOP"])
        assert opts.stop_sequences == ["END", "STOP"]

    def test_all_custom_values(self):
        """Test setting all custom values."""
        opts = LLMOptions(
            temperature=0.5,
            max_tokens=1000,
            top_p=0.95,
            stop_sequences=["###"]
        )
        assert opts.temperature == 0.5
        assert opts.max_tokens == 1000
        assert opts.top_p == 0.95
        assert opts.stop_sequences == ["###"]


class TestTokenUsage:
    """Test cases for TokenUsage dataclass."""

    def test_create_token_usage(self):
        """Test creating token usage."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_token_usage_equality(self):
        """Test token usage equality."""
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        usage2 = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert usage1 == usage2


class TestLLMResponse:
    """Test cases for LLMResponse dataclass."""

    def test_create_minimal_response(self):
        """Test creating response with required fields only."""
        response = LLMResponse(
            content="Hello world",
            model="test-model",
            provider=LLMProviderType.OLLAMA
        )
        assert response.content == "Hello world"
        assert response.model == "test-model"
        assert response.provider == LLMProviderType.OLLAMA
        assert response.tokens is None
        assert response.duration is None
        assert response.raw_response is None

    def test_create_full_response(self):
        """Test creating response with all fields."""
        tokens = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        response = LLMResponse(
            content="Test response",
            model="claude-sonnet-4-20250514",
            provider=LLMProviderType.ANTHROPIC,
            tokens=tokens,
            duration=1.5,
            raw_response={"id": "msg_123"}
        )
        assert response.content == "Test response"
        assert response.model == "claude-sonnet-4-20250514"
        assert response.provider == LLMProviderType.ANTHROPIC
        assert response.tokens.total_tokens == 30
        assert response.duration == 1.5
        assert response.raw_response == {"id": "msg_123"}

    def test_to_legacy_format(self):
        """Test conversion to legacy Ollama format."""
        tokens = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        response = LLMResponse(
            content="Test content",
            model="test-model",
            provider=LLMProviderType.OLLAMA,
            tokens=tokens,
            duration=2.0
        )

        legacy = response.to_legacy_format()

        assert legacy["message"]["content"] == "Test content"
        assert legacy["prompt_eval_count"] == 10
        assert legacy["eval_count"] == 20

    def test_to_legacy_format_no_tokens(self):
        """Test legacy format when tokens are None."""
        response = LLMResponse(
            content="Test",
            model="model",
            provider=LLMProviderType.OPENAI
        )

        legacy = response.to_legacy_format()

        assert legacy["message"]["content"] == "Test"
        # No token keys when tokens is None
        assert "eval_count" not in legacy
        assert "prompt_eval_count" not in legacy

    def test_response_providers(self):
        """Test response with different providers."""
        for provider in LLMProviderType:
            response = LLMResponse(
                content="test",
                model="test-model",
                provider=provider
            )
            assert response.provider == provider

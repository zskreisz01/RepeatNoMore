"""LLM provider abstraction module.

This module provides a unified interface for interacting with various LLM providers
including Anthropic (Claude), OpenAI (ChatGPT), and Cursor.

Example usage:
    from app.llm import get_llm_provider, LLMMessage, LLMOptions

    # Get default provider (from settings)
    provider = get_llm_provider()

    # Or specify a provider
    provider = get_llm_provider(provider="anthropic", model="claude-sonnet-4-20250514")

    # Send a chat request
    messages = [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="Hello!"),
    ]
    options = LLMOptions(temperature=0.7, max_tokens=1000)

    response = provider.chat(messages, options)
    print(response.content)
"""

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
)
from app.llm.factory import LLMProviderFactory, get_llm_provider
from app.llm.providers import (
    AnthropicProvider,
    CursorProvider,
    OpenAIProvider,
)
from app.llm.types import (
    LLMMessage,
    LLMOptions,
    LLMProviderType,
    LLMResponse,
    TokenUsage,
)

__all__ = [
    # Main interface
    "get_llm_provider",
    "LLMProviderFactory",
    # Types
    "LLMMessage",
    "LLMOptions",
    "LLMResponse",
    "LLMProviderType",
    "TokenUsage",
    # Base class
    "BaseLLMProvider",
    # Providers
    "AnthropicProvider",
    "OpenAIProvider",
    "CursorProvider",
    # Exceptions
    "LLMError",
    "LLMConfigurationError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
]

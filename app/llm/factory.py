"""LLM provider factory."""

from typing import Any, Dict, Optional, Type

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import LLMConfigurationError
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.cursor import CursorProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.types import LLMProviderType


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""

    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "cursor": CursorProvider,
    }

    _instance_cache: Dict[str, BaseLLMProvider] = {}

    @classmethod
    def register_provider(
        cls, name: str, provider_class: Type[BaseLLMProvider]
    ) -> None:
        """Register a new provider type."""
        cls._providers[name.lower()] = provider_class

    @classmethod
    def get_provider_class(cls, provider: str) -> Type[BaseLLMProvider]:
        """Get the provider class for a given provider name."""
        provider = provider.lower()
        if provider not in cls._providers:
            raise LLMConfigurationError(
                f"Unknown provider: {provider}. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[provider]

    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        use_cache: bool = False,
        **kwargs: Any,
    ) -> BaseLLMProvider:
        """
        Create an LLM provider instance.

        Args:
            provider: Provider name (ollama, anthropic, openai, cursor)
                     If None, uses configured default from settings
            model: Model name. If None, uses provider default from settings
            use_cache: Whether to cache and reuse provider instances
            **kwargs: Additional provider-specific configuration

        Returns:
            BaseLLMProvider: Configured provider instance
        """
        from app.config import get_settings

        settings = get_settings()
        provider = provider or settings.llm_provider
        provider = provider.lower()

        # Get provider-specific config from settings
        config = cls._get_provider_config(provider, settings)
        config.update(kwargs)

        # Use provided model or default from config
        if model:
            config["model"] = model

        if "model" not in config or not config["model"]:
            raise LLMConfigurationError(f"No model specified for {provider}")

        # Check cache if requested
        if use_cache:
            cache_key = f"{provider}:{config['model']}"
            if cache_key in cls._instance_cache:
                return cls._instance_cache[cache_key]

        provider_class = cls.get_provider_class(provider)
        instance = provider_class(**config)

        if use_cache:
            cache_key = f"{provider}:{config['model']}"
            cls._instance_cache[cache_key] = instance

        return instance

    @classmethod
    def _get_provider_config(cls, provider: str, settings: Any) -> Dict[str, Any]:
        """Get configuration for a specific provider from settings."""
        configs: Dict[str, Dict[str, Any]] = {
            # Note: Ollama is not configured via settings - must be configured explicitly
            "ollama": {},
            "anthropic": {
                "api_key": settings.anthropic_api_key,
                "model": settings.anthropic_model,
                "max_tokens": settings.anthropic_max_tokens,
            },
            "openai": {
                "api_key": settings.openai_api_key,
                "model": settings.openai_model,
                "base_url": settings.openai_base_url or None,
            },
            "cursor": {
                "api_key": settings.cursor_api_key,
                "model": settings.cursor_model,
                "base_url": settings.cursor_base_url or None,
            },
        }

        return configs.get(provider, {})

    @classmethod
    def get_default(cls) -> BaseLLMProvider:
        """Get the default configured provider (cached)."""
        return cls.create(use_cache=True)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the provider cache."""
        cls._instance_cache.clear()

    @classmethod
    def list_providers(cls) -> list[str]:
        """List available provider names."""
        return list(cls._providers.keys())


def get_llm_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs: Any,
) -> BaseLLMProvider:
    """
    Get an LLM provider instance.

    Convenience function that wraps LLMProviderFactory.create().

    Args:
        provider: Provider name (ollama, anthropic, openai, cursor)
        model: Model name
        **kwargs: Additional configuration

    Returns:
        BaseLLMProvider: Configured provider
    """
    if provider is None and model is None and not kwargs:
        return LLMProviderFactory.get_default()
    return LLMProviderFactory.create(provider, model, **kwargs)

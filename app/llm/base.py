"""Base class for LLM providers."""

import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from app.llm.exceptions import LLMError
from app.llm.types import LLMMessage, LLMOptions, LLMProviderType, LLMResponse
from app.utils.logging import get_logger


class BaseLLMProvider(ABC):
    """Base class implementing common LLM provider functionality."""

    def __init__(self, model: str, **config: Any) -> None:
        """
        Initialize provider.

        Args:
            model: Model name/identifier
            **config: Provider-specific configuration
        """
        self.model = model
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.provider_name}")
        self._validate_config()

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name."""
        pass

    @property
    @abstractmethod
    def provider_type(self) -> LLMProviderType:
        """Return provider enum value."""
        pass

    @property
    def model_name(self) -> str:
        """Return current model name."""
        return self.model

    def _validate_config(self) -> None:
        """Validate provider configuration. Override for custom validation."""
        pass

    def _get_default_options(self) -> LLMOptions:
        """Get default options for this provider."""
        return LLMOptions()

    def _merge_options(self, options: Optional[LLMOptions]) -> LLMOptions:
        """Merge provided options with defaults."""
        if options is None:
            return self._get_default_options()
        return options

    @abstractmethod
    def _do_chat(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Provider-specific chat implementation."""
        pass

    def chat(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None,
    ) -> LLMResponse:
        """
        Send messages and get a response.

        Args:
            messages: List of conversation messages
            options: Generation options

        Returns:
            LLMResponse: Unified response object
        """
        start_time = time.time()
        merged_options = self._merge_options(options)

        self.logger.info(
            "llm_chat_request",
            provider=self.provider_name,
            model=self.model,
            message_count=len(messages),
        )

        try:
            response = self._do_chat(messages, merged_options)
            response.duration = time.time() - start_time

            self.logger.info(
                "llm_chat_response",
                provider=self.provider_name,
                model=self.model,
                duration=response.duration,
                tokens=response.tokens.total_tokens if response.tokens else None,
            )

            return response

        except Exception as e:
            self.logger.error(
                "llm_chat_failed",
                provider=self.provider_name,
                model=self.model,
                error=str(e),
            )
            raise LLMError(f"{self.provider_name} chat failed: {e}") from e

    async def achat(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None,
    ) -> LLMResponse:
        """
        Async version of chat.

        Default implementation runs sync version in thread pool.
        Override for true async support.
        """
        import asyncio

        return await asyncio.to_thread(self.chat, messages, options)

    def stream(
        self,
        messages: List[LLMMessage],
        options: Optional[LLMOptions] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens. Override for streaming support."""
        raise NotImplementedError(f"{self.provider_name} does not support streaming")

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        pass

    def list_models(self) -> List[str]:
        """List available models. Override if provider supports this."""
        return [self.model]

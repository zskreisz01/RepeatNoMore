"""Anthropic/Claude LLM provider."""

from typing import Any, List, Optional, Tuple

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import LLMAuthenticationError, LLMConfigurationError
from app.llm.types import (
    LLMMessage,
    LLMOptions,
    LLMProviderType,
    LLMResponse,
    TokenUsage,
)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider implementation."""

    def __init__(
        self,
        model: str,
        api_key: str,
        max_tokens: int = 4096,
        **config: Any,
    ) -> None:
        """
        Initialize Anthropic provider.

        Args:
            model: Model name (e.g., 'claude-sonnet-4-20250514')
            api_key: Anthropic API key
            max_tokens: Default max tokens for responses
            **config: Additional configuration
        """
        self.api_key = api_key
        self.max_tokens = max_tokens
        self._client: Any = None
        super().__init__(model, **config)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.ANTHROPIC

    @property
    def client(self) -> Any:
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise LLMConfigurationError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        return self._client

    def _validate_config(self) -> None:
        """Validate Anthropic configuration."""
        if not self.api_key:
            raise LLMConfigurationError("Anthropic API key is required")

    def _convert_messages(
        self, messages: List[LLMMessage]
    ) -> Tuple[Optional[str], List[dict]]:
        """Convert messages to Anthropic format (system separate from messages)."""
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                chat_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        return system_message, chat_messages

    def _do_chat(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Execute chat with Anthropic."""
        system_message, chat_messages = self._convert_messages(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages,
            "max_tokens": options.max_tokens or self.max_tokens,
            "temperature": options.temperature,
        }

        if system_message:
            kwargs["system"] = system_message

        if options.stop_sequences:
            kwargs["stop_sequences"] = options.stop_sequences

        try:
            response = self.client.messages.create(**kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            if "authentication" in error_msg or "api key" in error_msg:
                raise LLMAuthenticationError(f"Anthropic authentication failed: {e}")
            raise

        # Extract content
        content = ""
        if response.content:
            content = response.content[0].text

        # Extract token usage
        tokens = TokenUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider_type,
            tokens=tokens,
            raw_response=(
                response.model_dump() if hasattr(response, "model_dump") else None
            ),
        )

    def is_available(self) -> bool:
        """Check if Anthropic is configured and available."""
        if not self.api_key:
            return False
        try:
            # Just check that client can be created
            _ = self.client
            return True
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List available Claude models."""
        # Anthropic doesn't have a models list API, return known models
        return [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]

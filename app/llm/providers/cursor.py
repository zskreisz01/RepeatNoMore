"""Cursor LLM provider."""

from typing import Any, Dict, List, Optional

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import LLMAuthenticationError, LLMConfigurationError
from app.llm.types import (
    LLMMessage,
    LLMOptions,
    LLMProviderType,
    LLMResponse,
    TokenUsage,
)


class CursorProvider(BaseLLMProvider):
    """Cursor LLM provider implementation.

    Cursor uses OpenAI-compatible API endpoints, but is implemented as a
    separate provider for explicit configuration and future extensibility.
    """

    DEFAULT_BASE_URL = "https://api.cursor.sh/v1"

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        **config: Any,
    ) -> None:
        """
        Initialize Cursor provider.

        Args:
            model: Model name (e.g., 'cursor-small')
            api_key: Cursor API key
            base_url: Optional custom base URL (defaults to Cursor API)
            **config: Additional configuration
        """
        self.api_key = api_key
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self._client: Any = None
        super().__init__(model, **config)

    @property
    def provider_name(self) -> str:
        return "cursor"

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.CURSOR

    @property
    def client(self) -> Any:
        """Lazy-load OpenAI-compatible client for Cursor."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise LLMConfigurationError(
                    "openai package not installed. Run: pip install openai"
                )
        return self._client

    def _validate_config(self) -> None:
        """Validate Cursor configuration."""
        if not self.api_key:
            raise LLMConfigurationError("Cursor API key is required")

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """Convert LLMMessage to OpenAI format."""
        return [{"role": m.role, "content": m.content} for m in messages]

    def _do_chat(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Execute chat with Cursor API."""
        cursor_messages = self._convert_messages(messages)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": cursor_messages,
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
        }

        if options.top_p is not None:
            kwargs["top_p"] = options.top_p
        if options.stop_sequences:
            kwargs["stop"] = options.stop_sequences

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            if "authentication" in error_msg or "api key" in error_msg:
                raise LLMAuthenticationError(f"Cursor authentication failed: {e}")
            raise

        # Extract content
        content = response.choices[0].message.content or ""

        # Extract token usage
        tokens = None
        if response.usage:
            tokens = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
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
        """Check if Cursor is configured and available."""
        if not self.api_key:
            return False
        try:
            _ = self.client
            return True
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List available Cursor models."""
        # Cursor models - update as they add more
        return [
            "cursor-small",
            "cursor-large",
        ]

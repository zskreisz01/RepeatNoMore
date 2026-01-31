"""OpenAI/ChatGPT LLM provider."""

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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI ChatGPT LLM provider implementation."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        **config: Any,
    ) -> None:
        """
        Initialize OpenAI provider.

        Args:
            model: Model name (e.g., 'gpt-4-turbo-preview')
            api_key: OpenAI API key
            base_url: Optional custom base URL (for Azure OpenAI)
            organization: Optional organization ID
            **config: Additional configuration
        """
        self.api_key = api_key
        self.base_url = base_url
        self.organization = organization
        self._client: Any = None
        super().__init__(model, **config)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OPENAI

    @property
    def client(self) -> Any:
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                kwargs: Dict[str, Any] = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                if self.organization:
                    kwargs["organization"] = self.organization

                self._client = OpenAI(**kwargs)
            except ImportError:
                raise LLMConfigurationError(
                    "openai package not installed. Run: pip install openai"
                )
        return self._client

    def _validate_config(self) -> None:
        """Validate OpenAI configuration."""
        if not self.api_key:
            raise LLMConfigurationError("OpenAI API key is required")

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """Convert LLMMessage to OpenAI format."""
        return [{"role": m.role, "content": m.content} for m in messages]

    def _do_chat(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Execute chat with OpenAI."""
        openai_messages = self._convert_messages(messages)

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
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
                raise LLMAuthenticationError(f"OpenAI authentication failed: {e}")
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
        """Check if OpenAI is configured and available."""
        if not self.api_key:
            return False
        try:
            _ = self.client
            return True
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List available OpenAI models."""
        try:
            models = self.client.models.list()
            return [m.id for m in models.data if "gpt" in m.id.lower()]
        except Exception:
            return [
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-3.5-turbo",
            ]

"""Ollama LLM provider."""

from typing import Any, Dict, List

import ollama

from app.llm.base import BaseLLMProvider
from app.llm.exceptions import LLMConfigurationError, LLMConnectionError
from app.llm.types import (
    LLMMessage,
    LLMOptions,
    LLMProviderType,
    LLMResponse,
    TokenUsage,
)


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider implementation."""

    def __init__(
        self,
        model: str,
        host: str = "localhost",
        port: int = 11434,
        **config: Any,
    ) -> None:
        """
        Initialize Ollama provider.

        Args:
            model: Model name (e.g., 'mistral:7b-instruct')
            host: Ollama server host
            port: Ollama server port
            **config: Additional configuration
        """
        self.host = host
        self.port = port
        super().__init__(model, **config)

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.OLLAMA

    @property
    def base_url(self) -> str:
        """Get the Ollama server URL."""
        return f"http://{self.host}:{self.port}"

    def _validate_config(self) -> None:
        """Validate Ollama configuration."""
        if not self.host:
            raise LLMConfigurationError("Ollama host is required")
        if not self.model:
            raise LLMConfigurationError("Ollama model is required")

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """Convert LLMMessage to Ollama format."""
        return [{"role": m.role, "content": m.content} for m in messages]

    def _do_chat(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Execute chat with Ollama."""
        ollama_messages = self._convert_messages(messages)

        # Map options to Ollama format
        ollama_options: Dict[str, Any] = {
            "temperature": options.temperature,
            "num_predict": options.max_tokens,
        }
        if options.top_p is not None:
            ollama_options["top_p"] = options.top_p
        if options.stop_sequences:
            ollama_options["stop"] = options.stop_sequences

        response = ollama.chat(
            model=self.model,
            messages=ollama_messages,
            options=ollama_options,
        )

        # Extract token usage
        tokens = None
        if "prompt_eval_count" in response or "eval_count" in response:
            prompt_tokens = response.get("prompt_eval_count", 0)
            completion_tokens = response.get("eval_count", 0)
            tokens = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

        return LLMResponse(
            content=response["message"]["content"],
            model=self.model,
            provider=self.provider_type,
            tokens=tokens,
            raw_response=response,
        )

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            ollama.list()
            return True
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            available = ollama.list()
            models_list = (
                available.get("models", [])
                if isinstance(available, dict)
                else getattr(available, "models", [])
            )
            return [
                m.get("name") if isinstance(m, dict) else getattr(m, "model", "")
                for m in models_list
            ]
        except Exception:
            return []

"""Type definitions for LLM module."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LLMProviderType(Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    CURSOR = "cursor"


@dataclass
class LLMMessage:
    """A message in the conversation."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMOptions:
    """Options for LLM generation."""

    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: Optional[float] = None
    stop_sequences: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.top_p is not None:
            result["top_p"] = self.top_p
        if self.stop_sequences is not None:
            result["stop_sequences"] = self.stop_sequences
        return result


@dataclass
class TokenUsage:
    """Token usage information."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "TokenUsage":
        """Create TokenUsage from a dictionary."""
        prompt = data.get("prompt", data.get("prompt_tokens", 0))
        completion = data.get("completion", data.get("completion_tokens", 0))
        total = data.get("total", data.get("total_tokens", prompt + completion))
        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
        )


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""

    content: str
    model: str
    provider: LLMProviderType
    tokens: Optional[TokenUsage] = None
    raw_response: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None

    def to_legacy_format(self) -> Dict[str, Any]:
        """
        Convert to legacy Ollama-compatible format for backward compatibility.

        Returns format expected by existing code:
        {"message": {"content": "..."}, "prompt_eval_count": N, "eval_count": N}
        """
        response: Dict[str, Any] = {"message": {"content": self.content}}
        if self.tokens:
            response["prompt_eval_count"] = self.tokens.prompt_tokens
            response["eval_count"] = self.tokens.completion_tokens
        return response

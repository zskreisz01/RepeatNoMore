"""Shared utilities and base classes for agents."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgentType(Enum):
    """Types of agents in the system."""

    QA = "qa"
    CODE_REVIEW = "code_review"
    DEBUG = "debug"
    SUPERVISOR = "supervisor"
    CONFIG_CHECKER = "config_checker"


class AgentStatus(Enum):
    """Status of agent execution."""

    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentResult:
    """Result from an agent execution."""

    success: bool
    output: Any
    metadata: Dict[str, Any]
    error: Optional[str] = None
    processing_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "metadata": self.metadata,
            "error": self.error,
            "processing_time": self.processing_time
        }


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, agent_type: AgentType):
        """
        Initialize base agent.

        Args:
            agent_type: Type of agent
        """
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        self.logger = get_logger(f"{__name__}.{agent_type.value}")

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Process input and return result.

        Args:
            input_data: Input data for processing

        Returns:
            AgentResult: Processing result
        """
        pass

    def _set_status(self, status: AgentStatus) -> None:
        """
        Update agent status.

        Args:
            status: New status
        """
        self.status = status
        self.logger.info("agent_status_changed", status=status.value)

    def _validate_input(self, input_data: Dict[str, Any], required_keys: List[str]) -> None:
        """
        Validate that input contains required keys.

        Args:
            input_data: Input data to validate
            required_keys: List of required keys

        Raises:
            ValueError: If required keys are missing
        """
        missing_keys = [key for key in required_keys if key not in input_data]
        if missing_keys:
            raise ValueError(f"Missing required keys: {missing_keys}")


class PromptBuilder:
    """Helper class for building LLM prompts."""

    @staticmethod
    def build_system_prompt(role: str, capabilities: List[str], guidelines: List[str]) -> str:
        """
        Build a system prompt for an agent.

        Args:
            role: Agent's role description
            capabilities: List of agent capabilities
            guidelines: List of guidelines for the agent

        Returns:
            str: Formatted system prompt
        """
        prompt = f"You are {role}.\n\n"

        if capabilities:
            prompt += "Your capabilities:\n"
            for i, cap in enumerate(capabilities, 1):
                prompt += f"{i}. {cap}\n"
            prompt += "\n"

        if guidelines:
            prompt += "Guidelines:\n"
            for i, guideline in enumerate(guidelines, 1):
                prompt += f"{i}. {guideline}\n"
            prompt += "\n"

        return prompt

    @staticmethod
    def format_context(context_items: List[Dict[str, str]]) -> str:
        """
        Format context items into a readable string.

        Args:
            context_items: List of context dictionaries with 'title' and 'content'

        Returns:
            str: Formatted context string
        """
        formatted = "# Context\n\n"

        for item in context_items:
            title = item.get("title", "Untitled")
            content = item.get("content", "")
            formatted += f"## {title}\n{content}\n\n"

        return formatted

    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """
        Format code in markdown code block.

        Args:
            code: Code to format
            language: Programming language for syntax highlighting

        Returns:
            str: Formatted code block
        """
        return f"```{language}\n{code}\n```"


class ResponseFormatter:
    """Helper class for formatting agent responses."""

    @staticmethod
    def format_list(items: List[str], numbered: bool = True) -> str:
        """
        Format list of items.

        Args:
            items: List of items to format
            numbered: Whether to use numbered list

        Returns:
            str: Formatted list
        """
        if numbered:
            return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))
        else:
            return "\n".join(f"- {item}" for item in items)

    @staticmethod
    def format_section(title: str, content: str, level: int = 2) -> str:
        """
        Format a section with title and content.

        Args:
            title: Section title
            content: Section content
            level: Heading level (1-6)

        Returns:
            str: Formatted section
        """
        heading = "#" * level
        return f"{heading} {title}\n\n{content}\n"

    @staticmethod
    def format_code_review_finding(
        severity: str,
        line_number: Optional[int],
        description: str,
        suggestion: Optional[str] = None
    ) -> str:
        """
        Format a code review finding.

        Args:
            severity: Severity level (info, warning, error)
            line_number: Line number of the issue
            description: Description of the finding
            suggestion: Optional suggestion for fix

        Returns:
            str: Formatted finding
        """
        emoji_map = {
            "error": "🔴",
            "warning": "🟡",
            "info": "🔵"
        }

        emoji = emoji_map.get(severity.lower(), "⚪")
        location = f"Line {line_number}: " if line_number else ""

        result = f"{emoji} **{severity.upper()}** {location}{description}"

        if suggestion:
            result += f"\n  💡 Suggestion: {suggestion}"

        return result


class ContextManager:
    """Manage conversation context for agents."""

    def __init__(self, max_history: int = 10):
        """
        Initialize context manager.

        Args:
            max_history: Maximum number of messages to keep in history
        """
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the history.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.history.append({"role": role, "content": content})

        # Trim history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get conversation history.

        Returns:
            List[Dict[str, str]]: Message history
        """
        return self.history.copy()

    def clear(self) -> None:
        """Clear conversation history."""
        self.history = []

    def get_context_string(self) -> str:
        """
        Get history as a formatted string.

        Returns:
            str: Formatted conversation history
        """
        if not self.history:
            return "No previous conversation."

        formatted = "# Previous Conversation\n\n"
        for msg in self.history:
            role = msg["role"].capitalize()
            content = msg["content"]
            formatted += f"**{role}:** {content}\n\n"

        return formatted


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """
    Extract code blocks from markdown text.

    Args:
        text: Markdown text

    Returns:
        List[Dict[str, str]]: List of code blocks with language and content
    """
    import re

    pattern = r"```(\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    code_blocks = []
    for language, code in matches:
        code_blocks.append({
            "language": language or "text",
            "code": code.strip()
        })

    return code_blocks


def calculate_confidence(scores: List[float]) -> float:
    """
    Calculate confidence score from retrieval scores.

    Args:
        scores: List of similarity scores

    Returns:
        float: Confidence score (0-1)
    """
    if not scores:
        return 0.0

    # Use weighted average, giving more weight to top results
    weights = [1.0 / (i + 1) for i in range(len(scores))]
    weighted_sum = sum(s * w for s, w in zip(scores, weights))
    weight_sum = sum(weights)

    return min(0.95, weighted_sum / weight_sum)  # Cap at 0.95

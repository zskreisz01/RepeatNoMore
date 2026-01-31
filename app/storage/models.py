"""Data models for storage entities."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class Language(Enum):
    """Supported languages."""

    EN = "en"
    HU = "hu"


class DraftStatus(Enum):
    """Status of a draft update."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class QuestionStatus(Enum):
    """Status of a pending question."""

    PENDING = "pending"
    ANSWERED = "answered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    ON_HOLD = "on_hold"


class FeatureStatus(Enum):
    """Status of a feature suggestion."""

    OPEN = "open"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


def _generate_draft_id() -> str:
    """Generate a unique draft ID."""
    return f"DRAFT-{uuid.uuid4().hex[:8].upper()}"


def _generate_question_id() -> str:
    """Generate a unique question ID."""
    return f"Q-{uuid.uuid4().hex[:8].upper()}"


def _generate_feature_id() -> str:
    """Generate a unique feature ID."""
    return f"FEAT-{uuid.uuid4().hex[:8].upper()}"


def _current_timestamp() -> str:
    """Get current timestamp as ISO format string."""
    return datetime.utcnow().isoformat()


@dataclass
class DraftUpdate:
    """A draft documentation update proposed by a user."""

    id: str = field(default_factory=_generate_draft_id)
    user_email: str = ""
    user_name: str = ""
    content: str = ""
    target_section: str = ""
    description: str = ""
    language: str = field(default=Language.EN.value)
    status: str = field(default=DraftStatus.PENDING.value)
    created_at: str = field(default_factory=_current_timestamp)
    updated_at: str = field(default_factory=_current_timestamp)
    approved_by: Optional[str] = None
    applied_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DraftUpdate":
        """Create from dictionary."""
        return cls(**data)

    def approve(self, approved_by: str) -> None:
        """Mark draft as approved."""
        self.status = DraftStatus.APPROVED.value
        self.approved_by = approved_by
        self.updated_at = _current_timestamp()

    def reject(self, reason: str) -> None:
        """Mark draft as rejected."""
        self.status = DraftStatus.REJECTED.value
        self.rejection_reason = reason
        self.updated_at = _current_timestamp()

    def mark_applied(self) -> None:
        """Mark draft as applied to documentation."""
        self.status = DraftStatus.APPLIED.value
        self.applied_at = _current_timestamp()
        self.updated_at = _current_timestamp()


@dataclass
class PendingQuestion:
    """A question that has been escalated to admins."""

    id: str = field(default_factory=_generate_question_id)
    user_email: str = ""
    user_name: str = ""
    question: str = ""
    bot_answer: str = ""
    rejection_reason: Optional[str] = None
    language: str = field(default=Language.EN.value)
    status: str = field(default=QuestionStatus.ESCALATED.value)
    platform: str = "api"
    conversation_id: Optional[str] = None
    created_at: str = field(default_factory=_current_timestamp)
    updated_at: str = field(default_factory=_current_timestamp)
    admin_response: Optional[str] = None
    responded_by: Optional[str] = None
    responded_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PendingQuestion":
        """Create from dictionary."""
        return cls(**data)

    def respond(self, admin_email: str, response: str) -> None:
        """Record admin response to the question."""
        self.admin_response = response
        self.responded_by = admin_email
        self.responded_at = _current_timestamp()
        self.status = QuestionStatus.ANSWERED.value
        self.updated_at = _current_timestamp()

    def put_on_hold(self) -> None:
        """Put the question on hold."""
        self.status = QuestionStatus.ON_HOLD.value
        self.updated_at = _current_timestamp()


@dataclass
class FeatureSuggestion:
    """A feature suggestion from a user."""

    id: str = field(default_factory=_generate_feature_id)
    user_email: str = ""
    user_name: str = ""
    title: str = ""
    description: str = ""
    language: str = field(default=Language.EN.value)
    status: str = field(default=FeatureStatus.OPEN.value)
    created_at: str = field(default_factory=_current_timestamp)
    updated_at: str = field(default_factory=_current_timestamp)
    votes: int = 0
    comments: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeatureSuggestion":
        """Create from dictionary."""
        return cls(**data)

    def upvote(self) -> None:
        """Increment vote count."""
        self.votes += 1
        self.updated_at = _current_timestamp()

    def add_comment(self, user_email: str, comment: str) -> None:
        """Add a comment to the suggestion."""
        self.comments.append({
            "user_email": user_email,
            "comment": comment,
            "created_at": _current_timestamp()
        })
        self.updated_at = _current_timestamp()

    def update_status(self, status: FeatureStatus) -> None:
        """Update the feature status."""
        self.status = status.value
        self.updated_at = _current_timestamp()


@dataclass
class AcceptedQA:
    """An accepted Q&A pair to be saved to documentation."""

    id: str = field(default_factory=lambda: f"QA-{uuid.uuid4().hex[:8].upper()}")
    question: str = ""
    answer: str = ""
    user_email: str = ""
    language: str = field(default=Language.EN.value)
    created_at: str = field(default_factory=_current_timestamp)
    sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AcceptedQA":
        """Create from dictionary."""
        return cls(**data)

    def to_markdown(self) -> str:
        """Convert to markdown format for documentation."""
        return f"""### {self.question}
<!-- QA_ID: {self.id} -->

{self.answer}

_ID: {self.id} | Accepted on {self.created_at[:10]}_

---
"""

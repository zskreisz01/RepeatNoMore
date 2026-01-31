"""Event types for the RepeatNoMore event system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class DocumentEvent(str, Enum):
    """Event types for document-related operations."""

    # Draft events
    DRAFT_CREATED = "draft.created"
    DRAFT_APPROVED = "draft.approved"
    DRAFT_REJECTED = "draft.rejected"
    DRAFT_CHANGED = "draft.changed"

    # Question events
    QUESTION_CREATED = "question.created"
    QUESTION_ANSWERED = "question.answered"

    # Document events
    DOC_UPDATED = "doc.updated"
    DOC_CREATED = "doc.created"
    DOC_DELETED = "doc.deleted"

    # Git events
    GIT_SYNC_REQUESTED = "git.sync_requested"
    GIT_SYNC_COMPLETED = "git.sync_completed"


@dataclass
class EventData:
    """Container for event data."""

    event_type: DocumentEvent
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "system"

    # Common fields
    user_email: Optional[str] = None
    file_path: Optional[str] = None

    # Draft-specific fields
    draft_id: Optional[str] = None
    draft_content: Optional[str] = None
    target_section: Optional[str] = None

    # Question-specific fields
    question_id: Optional[str] = None
    question_text: Optional[str] = None
    answer_text: Optional[str] = None

    # Git-specific fields
    commit_sha: Optional[str] = None
    branch_name: Optional[str] = None

    # Additional context
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event data to dictionary."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "source": self.source,
            "user_email": self.user_email,
            "file_path": self.file_path,
            "draft_id": self.draft_id,
            "draft_content": self.draft_content,
            "target_section": self.target_section,
            "question_id": self.question_id,
            "question_text": self.question_text,
            "answer_text": self.answer_text,
            "commit_sha": self.commit_sha,
            "branch_name": self.branch_name,
            "metadata": self.metadata,
        }

"""Repository for draft update storage operations."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.storage.json_storage import JSONStorage
from app.storage.models import DraftUpdate, DraftStatus
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class DraftRepository:
    """Repository for managing draft updates."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize draft repository.

        Args:
            storage_path: Optional custom path for storage file
        """
        if storage_path is None:
            settings = get_settings()
            base_path = Path(settings.docs_repo_path).parent.parent / "data" / "storage"
            storage_path = str(base_path / "drafts.json")

        self.storage = JSONStorage[DraftUpdate](storage_path, collection_name="drafts")
        logger.info("draft_repository_initialized", path=storage_path)

    def add(self, draft: DraftUpdate) -> DraftUpdate:
        """
        Add a new draft update.

        Args:
            draft: The draft update to add

        Returns:
            The added draft with ID
        """
        self.storage.add(draft.to_dict())
        logger.info("draft_added", id=draft.id, user=draft.user_email)
        return draft

    def get(self, draft_id: str) -> Optional[DraftUpdate]:
        """
        Get a draft by ID.

        Args:
            draft_id: The draft ID

        Returns:
            The draft if found, None otherwise
        """
        data = self.storage.get_by_id(draft_id)
        if data:
            return DraftUpdate.from_dict(data)
        return None

    def get_all(self) -> list[DraftUpdate]:
        """Get all drafts."""
        items = self.storage.get_all()
        return [DraftUpdate.from_dict(item) for item in items]

    def get_pending(self) -> list[DraftUpdate]:
        """Get all pending drafts."""
        items = self.storage.query({"status": DraftStatus.PENDING.value})
        return [DraftUpdate.from_dict(item) for item in items]

    def get_by_user(self, user_email: str) -> list[DraftUpdate]:
        """Get all drafts by a specific user."""
        items = self.storage.query({"user_email": user_email})
        return [DraftUpdate.from_dict(item) for item in items]

    def get_by_status(self, status: DraftStatus) -> list[DraftUpdate]:
        """Get all drafts with a specific status."""
        items = self.storage.query({"status": status.value})
        return [DraftUpdate.from_dict(item) for item in items]

    def update(self, draft: DraftUpdate) -> Optional[DraftUpdate]:
        """
        Update an existing draft.

        Args:
            draft: The draft with updated values

        Returns:
            The updated draft if found, None otherwise
        """
        result = self.storage.update(draft.id, draft.to_dict())
        if result:
            logger.info("draft_updated", id=draft.id, status=draft.status)
            return DraftUpdate.from_dict(result)
        return None

    def approve(self, draft_id: str, approved_by: str) -> Optional[DraftUpdate]:
        """
        Approve a draft.

        Args:
            draft_id: The draft ID
            approved_by: Email of the admin approving

        Returns:
            The updated draft if found, None otherwise
        """
        draft = self.get(draft_id)
        if draft:
            draft.approve(approved_by)
            return self.update(draft)
        return None

    def reject(self, draft_id: str, reason: str) -> Optional[DraftUpdate]:
        """
        Reject a draft.

        Args:
            draft_id: The draft ID
            reason: Reason for rejection

        Returns:
            The updated draft if found, None otherwise
        """
        draft = self.get(draft_id)
        if draft:
            draft.reject(reason)
            return self.update(draft)
        return None

    def mark_applied(self, draft_id: str) -> Optional[DraftUpdate]:
        """
        Mark a draft as applied.

        Args:
            draft_id: The draft ID

        Returns:
            The updated draft if found, None otherwise
        """
        draft = self.get(draft_id)
        if draft:
            draft.mark_applied()
            return self.update(draft)
        return None

    def delete(self, draft_id: str) -> bool:
        """
        Delete a draft.

        Args:
            draft_id: The draft ID

        Returns:
            True if deleted, False if not found
        """
        return self.storage.delete(draft_id)

    def count(self) -> int:
        """Get total draft count."""
        return self.storage.count()

    def count_pending(self) -> int:
        """Get count of pending drafts."""
        return len(self.get_pending())


# Global instance
_draft_repository: Optional[DraftRepository] = None


@lru_cache()
def get_draft_repository() -> DraftRepository:
    """
    Get or create a global draft repository instance.

    Returns:
        DraftRepository: The draft repository
    """
    global _draft_repository
    if _draft_repository is None:
        _draft_repository = DraftRepository()
    return _draft_repository

"""Repository for pending question queue storage operations."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.storage.json_storage import JSONStorage
from app.storage.models import PendingQuestion, QuestionStatus
from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class QueueRepository:
    """Repository for managing the pending question queue."""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize queue repository.

        Args:
            storage_path: Optional custom path for storage file
        """
        if storage_path is None:
            settings = get_settings()
            base_path = Path(settings.docs_repo_path).parent.parent / "data" / "storage"
            storage_path = str(base_path / "question_queue.json")

        self.storage = JSONStorage[PendingQuestion](storage_path, collection_name="questions")
        logger.info("queue_repository_initialized", path=storage_path)

    def add(self, question: PendingQuestion) -> PendingQuestion:
        """
        Add a new question to the queue.

        Args:
            question: The pending question to add

        Returns:
            The added question with ID
        """
        self.storage.add(question.to_dict())
        logger.info("question_added_to_queue", id=question.id, user=question.user_email)
        return question

    def get(self, question_id: str) -> Optional[PendingQuestion]:
        """
        Get a question by ID.

        Args:
            question_id: The question ID

        Returns:
            The question if found, None otherwise
        """
        data = self.storage.get_by_id(question_id)
        if data:
            return PendingQuestion.from_dict(data)
        return None

    def get_all(self) -> list[PendingQuestion]:
        """Get all questions in the queue."""
        items = self.storage.get_all()
        return [PendingQuestion.from_dict(item) for item in items]

    def get_pending(self) -> list[PendingQuestion]:
        """Get all escalated/pending questions."""
        items = self.storage.query({"status": QuestionStatus.ESCALATED.value})
        return [PendingQuestion.from_dict(item) for item in items]

    def get_on_hold(self) -> list[PendingQuestion]:
        """Get all questions on hold."""
        items = self.storage.query({"status": QuestionStatus.ON_HOLD.value})
        return [PendingQuestion.from_dict(item) for item in items]

    def get_by_platform(self, platform: str) -> list[PendingQuestion]:
        """Get all questions from a specific platform."""
        items = self.storage.query({"platform": platform})
        return [PendingQuestion.from_dict(item) for item in items]

    def get_by_user(self, user_email: str) -> list[PendingQuestion]:
        """Get all questions from a specific user."""
        items = self.storage.query({"user_email": user_email})
        return [PendingQuestion.from_dict(item) for item in items]

    def get_by_status(self, status: QuestionStatus) -> list[PendingQuestion]:
        """Get all questions with a specific status."""
        items = self.storage.query({"status": status.value})
        return [PendingQuestion.from_dict(item) for item in items]

    def update(self, question: PendingQuestion) -> Optional[PendingQuestion]:
        """
        Update an existing question.

        Args:
            question: The question with updated values

        Returns:
            The updated question if found, None otherwise
        """
        result = self.storage.update(question.id, question.to_dict())
        if result:
            logger.info("question_updated", id=question.id, status=question.status)
            return PendingQuestion.from_dict(result)
        return None

    def respond(
        self, question_id: str, admin_email: str, response: str
    ) -> Optional[PendingQuestion]:
        """
        Record an admin response to a question.

        Args:
            question_id: The question ID
            admin_email: Email of the responding admin
            response: The admin's response

        Returns:
            The updated question if found, None otherwise
        """
        question = self.get(question_id)
        if question:
            question.respond(admin_email, response)
            return self.update(question)
        return None

    def put_on_hold(self, question_id: str) -> Optional[PendingQuestion]:
        """
        Put a question on hold.

        Args:
            question_id: The question ID

        Returns:
            The updated question if found, None otherwise
        """
        question = self.get(question_id)
        if question:
            question.put_on_hold()
            return self.update(question)
        return None

    def delete(self, question_id: str) -> bool:
        """
        Delete a question from the queue.

        Args:
            question_id: The question ID

        Returns:
            True if deleted, False if not found
        """
        return self.storage.delete(question_id)

    def count(self) -> int:
        """Get total question count."""
        return self.storage.count()

    def count_pending(self) -> int:
        """Get count of pending questions."""
        return len(self.get_pending())


# Global instance
_queue_repository: Optional[QueueRepository] = None


@lru_cache()
def get_queue_repository() -> QueueRepository:
    """
    Get or create a global queue repository instance.

    Returns:
        QueueRepository: The queue repository
    """
    global _queue_repository
    if _queue_repository is None:
        _queue_repository = QueueRepository()
    return _queue_repository

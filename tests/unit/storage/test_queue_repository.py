"""Unit tests for queue repository."""

import pytest
from pathlib import Path

from app.storage.models import PendingQuestion, QuestionStatus
from app.storage.repositories.queue_repository import QueueRepository


class TestQueueRepository:
    """Tests for QueueRepository class."""

    @pytest.fixture
    def repository(self, tmp_path: Path) -> QueueRepository:
        """Create a queue repository instance."""
        storage_path = str(tmp_path / "question_queue.json")
        return QueueRepository(storage_path=storage_path)

    @pytest.fixture
    def sample_question(self) -> PendingQuestion:
        """Create a sample pending question."""
        return PendingQuestion(
            user_email="user@example.com",
            user_name="Test User",
            question="How do I configure the database?",
            bot_answer="You can configure the database by...",
            rejection_reason="The answer was incomplete",
            platform="discord"
        )

    def test_add_question(self, repository: QueueRepository, sample_question: PendingQuestion):
        """Test adding a question to the queue."""
        result = repository.add(sample_question)
        assert result.id == sample_question.id
        assert repository.count() == 1

    def test_get_question(self, repository: QueueRepository, sample_question: PendingQuestion):
        """Test getting a question by ID."""
        repository.add(sample_question)
        result = repository.get(sample_question.id)
        assert result is not None
        assert result.question == "How do I configure the database?"

    def test_get_question_not_found(self, repository: QueueRepository):
        """Test getting non-existent question."""
        result = repository.get("Q-NOTFOUND")
        assert result is None

    def test_get_all(self, repository: QueueRepository):
        """Test getting all questions."""
        repository.add(PendingQuestion(question="Q1?"))
        repository.add(PendingQuestion(question="Q2?"))
        questions = repository.get_all()
        assert len(questions) == 2

    def test_get_pending(self, repository: QueueRepository):
        """Test getting escalated questions."""
        q1 = PendingQuestion(question="Q1?")  # Escalated by default
        q2 = PendingQuestion(question="Q2?")
        q2.respond("admin@example.com", "Answer")

        repository.add(q1)
        repository.add(q2)

        pending = repository.get_pending()
        assert len(pending) == 1

    def test_get_on_hold(self, repository: QueueRepository):
        """Test getting questions on hold."""
        q1 = PendingQuestion(question="Q1?")
        q1.put_on_hold()
        q2 = PendingQuestion(question="Q2?")

        repository.add(q1)
        repository.add(q2)

        on_hold = repository.get_on_hold()
        assert len(on_hold) == 1

    def test_get_by_platform(self, repository: QueueRepository):
        """Test getting questions by platform."""
        repository.add(PendingQuestion(question="Q1?", platform="discord"))
        repository.add(PendingQuestion(question="Q2?", platform="discord"))
        repository.add(PendingQuestion(question="Q3?", platform="teams"))

        discord_questions = repository.get_by_platform("discord")
        assert len(discord_questions) == 2

    def test_get_by_user(self, repository: QueueRepository):
        """Test getting questions by user."""
        repository.add(PendingQuestion(user_email="user1@example.com", question="Q1?"))
        repository.add(PendingQuestion(user_email="user1@example.com", question="Q2?"))
        repository.add(PendingQuestion(user_email="user2@example.com", question="Q3?"))

        user1_questions = repository.get_by_user("user1@example.com")
        assert len(user1_questions) == 2

    def test_respond(self, repository: QueueRepository, sample_question: PendingQuestion):
        """Test responding to a question."""
        repository.add(sample_question)
        result = repository.respond(
            sample_question.id,
            "admin@example.com",
            "The correct answer is..."
        )
        assert result is not None
        assert result.status == QuestionStatus.ANSWERED.value
        assert result.admin_response == "The correct answer is..."
        assert result.responded_by == "admin@example.com"

    def test_put_on_hold(self, repository: QueueRepository, sample_question: PendingQuestion):
        """Test putting a question on hold."""
        repository.add(sample_question)
        result = repository.put_on_hold(sample_question.id)
        assert result is not None
        assert result.status == QuestionStatus.ON_HOLD.value

    def test_delete_question(self, repository: QueueRepository, sample_question: PendingQuestion):
        """Test deleting a question."""
        repository.add(sample_question)
        assert repository.count() == 1
        result = repository.delete(sample_question.id)
        assert result is True
        assert repository.count() == 0

    def test_count_pending(self, repository: QueueRepository):
        """Test counting pending questions."""
        q1 = PendingQuestion(question="Q1?")
        q2 = PendingQuestion(question="Q2?")
        q2.respond("admin@example.com", "Answer")

        repository.add(q1)
        repository.add(q2)

        assert repository.count() == 2
        assert repository.count_pending() == 1

    def test_get_by_status(self, repository: QueueRepository):
        """Test getting questions by status."""
        q1 = PendingQuestion(question="Q1?")
        q2 = PendingQuestion(question="Q2?")
        q2.put_on_hold()

        repository.add(q1)
        repository.add(q2)

        escalated = repository.get_by_status(QuestionStatus.ESCALATED)
        on_hold = repository.get_by_status(QuestionStatus.ON_HOLD)

        assert len(escalated) == 1
        assert len(on_hold) == 1

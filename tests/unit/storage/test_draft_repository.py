"""Unit tests for draft repository."""

import pytest
from pathlib import Path

from app.storage.models import DraftUpdate, DraftStatus
from app.storage.repositories.draft_repository import DraftRepository


class TestDraftRepository:
    """Tests for DraftRepository class."""

    @pytest.fixture
    def repository(self, tmp_path: Path) -> DraftRepository:
        """Create a draft repository instance."""
        storage_path = str(tmp_path / "drafts.json")
        return DraftRepository(storage_path=storage_path)

    @pytest.fixture
    def sample_draft(self) -> DraftUpdate:
        """Create a sample draft."""
        return DraftUpdate(
            user_email="user@example.com",
            user_name="Test User",
            content="Updated installation instructions",
            target_section="getting_started.md#installation",
            description="Fix outdated package version"
        )

    def test_add_draft(self, repository: DraftRepository, sample_draft: DraftUpdate):
        """Test adding a draft."""
        result = repository.add(sample_draft)
        assert result.id == sample_draft.id
        assert repository.count() == 1

    def test_get_draft(self, repository: DraftRepository, sample_draft: DraftUpdate):
        """Test getting a draft by ID."""
        repository.add(sample_draft)
        result = repository.get(sample_draft.id)
        assert result is not None
        assert result.user_email == "user@example.com"

    def test_get_draft_not_found(self, repository: DraftRepository):
        """Test getting non-existent draft."""
        result = repository.get("DRAFT-NOTFOUND")
        assert result is None

    def test_get_all(self, repository: DraftRepository):
        """Test getting all drafts."""
        repository.add(DraftUpdate(user_email="user1@example.com"))
        repository.add(DraftUpdate(user_email="user2@example.com"))
        drafts = repository.get_all()
        assert len(drafts) == 2

    def test_get_pending(self, repository: DraftRepository):
        """Test getting pending drafts."""
        draft1 = DraftUpdate(user_email="user1@example.com")
        draft2 = DraftUpdate(user_email="user2@example.com")
        draft2.approve("admin@example.com")

        repository.add(draft1)
        repository.add(draft2)

        pending = repository.get_pending()
        assert len(pending) == 1
        assert pending[0].user_email == "user1@example.com"

    def test_get_by_user(self, repository: DraftRepository):
        """Test getting drafts by user."""
        repository.add(DraftUpdate(user_email="user1@example.com"))
        repository.add(DraftUpdate(user_email="user1@example.com"))
        repository.add(DraftUpdate(user_email="user2@example.com"))

        user1_drafts = repository.get_by_user("user1@example.com")
        assert len(user1_drafts) == 2

    def test_get_by_status(self, repository: DraftRepository):
        """Test getting drafts by status."""
        draft1 = DraftUpdate(user_email="user@example.com")
        draft2 = DraftUpdate(user_email="user@example.com")
        draft2.approve("admin@example.com")

        repository.add(draft1)
        repository.add(draft2)

        approved = repository.get_by_status(DraftStatus.APPROVED)
        assert len(approved) == 1

    def test_update_draft(self, repository: DraftRepository, sample_draft: DraftUpdate):
        """Test updating a draft."""
        repository.add(sample_draft)
        sample_draft.content = "New content"
        result = repository.update(sample_draft)
        assert result is not None
        assert result.content == "New content"

    def test_approve_draft(self, repository: DraftRepository, sample_draft: DraftUpdate):
        """Test approving a draft."""
        repository.add(sample_draft)
        result = repository.approve(sample_draft.id, "admin@example.com")
        assert result is not None
        assert result.status == DraftStatus.APPROVED.value
        assert result.approved_by == "admin@example.com"

    def test_reject_draft(self, repository: DraftRepository, sample_draft: DraftUpdate):
        """Test rejecting a draft."""
        repository.add(sample_draft)
        result = repository.reject(sample_draft.id, "Invalid content")
        assert result is not None
        assert result.status == DraftStatus.REJECTED.value
        assert result.rejection_reason == "Invalid content"

    def test_mark_applied(self, repository: DraftRepository, sample_draft: DraftUpdate):
        """Test marking a draft as applied."""
        repository.add(sample_draft)
        repository.approve(sample_draft.id, "admin@example.com")
        result = repository.mark_applied(sample_draft.id)
        assert result is not None
        assert result.status == DraftStatus.APPLIED.value
        assert result.applied_at is not None

    def test_delete_draft(self, repository: DraftRepository, sample_draft: DraftUpdate):
        """Test deleting a draft."""
        repository.add(sample_draft)
        assert repository.count() == 1
        result = repository.delete(sample_draft.id)
        assert result is True
        assert repository.count() == 0

    def test_count_pending(self, repository: DraftRepository):
        """Test counting pending drafts."""
        draft1 = DraftUpdate(user_email="user@example.com")
        draft2 = DraftUpdate(user_email="user@example.com")
        draft2.approve("admin@example.com")

        repository.add(draft1)
        repository.add(draft2)

        assert repository.count() == 2
        assert repository.count_pending() == 1

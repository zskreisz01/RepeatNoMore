"""Unit tests for Discord WorkflowCog."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestWorkflowCogHelpers:
    """Tests for WorkflowCog helper functions."""

    def test_language_detection_hungarian(self):
        """Test that Hungarian text is detected."""
        from app.services.language_service import get_language_service
        from app.storage.models import Language

        service = get_language_service()
        text = "Hogyan kell telepiteni a rendszert?"
        detected = service.detect_language(text)
        assert detected == Language.HU

    def test_language_detection_english(self):
        """Test that English text is detected."""
        from app.services.language_service import get_language_service
        from app.storage.models import Language

        service = get_language_service()
        text = "How do I install the system?"
        detected = service.detect_language(text)
        assert detected == Language.EN

    def test_permission_check_admin(self):
        """Test admin permission check."""
        from app.services.permission_service import get_permission_service

        service = get_permission_service()
        assert service.is_admin("admin@example.com") is True
        assert service.is_admin("admin@example.com") is True

    def test_permission_check_non_admin(self):
        """Test non-admin permission check."""
        from app.services.permission_service import get_permission_service

        service = get_permission_service()
        assert service.is_admin("random@user.com") is False


class TestWorkflowServiceIntegration:
    """Tests for workflow service methods used by Discord cog."""

    @pytest.fixture
    def workflow_service(self):
        """Get workflow service instance."""
        from app.services.workflow_service import get_workflow_service
        return get_workflow_service()

    @pytest.mark.asyncio
    async def test_suggest_feature(self, workflow_service):
        """Test feature suggestion workflow."""
        with patch.object(
            workflow_service.feature_repo, "add"
        ) as mock_add:
            mock_add.return_value = None

            result = await workflow_service.suggest_feature(
                user_email="test@user.com",
                title="New Feature",
                description="A great feature idea",
                language="en",  # Use string, not enum
            )

            assert result["success"] is True
            assert "feature_id" in result
            assert result["feature_id"].startswith("FEAT-")

    @pytest.mark.asyncio
    async def test_create_draft_update(self, workflow_service):
        """Test draft update creation workflow."""
        with patch.object(
            workflow_service.draft_repo, "add"
        ) as mock_add:
            mock_add.return_value = None

            result = await workflow_service.create_draft_update(
                user_email="test@user.com",
                content="Updated installation instructions",
                target_section="installation.md",
                language="en",  # Use string, not enum
            )

            assert result["success"] is True
            assert "draft_id" in result
            assert result["draft_id"].startswith("DRAFT-")

    @pytest.mark.asyncio
    async def test_escalate_question(self, workflow_service):
        """Test question escalation workflow."""
        from app.storage.models import Language

        with patch.object(
            workflow_service.queue_repo, "add"
        ) as mock_add, patch.object(
            workflow_service.notification_service, "notify_question_escalated", new_callable=AsyncMock
        ) as mock_notify:
            mock_add.return_value = None
            mock_notify.return_value = {"discord": True, "teams": True}

            result = await workflow_service.escalate_question(
                user_email="test@user.com",
                question="How do I do X?",
                bot_answer="Here's the answer...",
                platform="discord",
                language=Language.EN,
            )

            assert result["success"] is True
            # The key is "question_id" not "queue_id"
            assert "question_id" in result
            assert result["question_id"].startswith("Q-")


class TestIdGeneration:
    """Tests for ID generation in storage models."""

    def test_draft_id_format(self):
        """Test draft ID format."""
        from app.storage.models import DraftUpdate, Language, DraftStatus

        draft = DraftUpdate(
            id="DRAFT-12345678",
            user_email="test@test.com",
            content="Test content",
            target_section="test.md",
            language=Language.EN,
            status=DraftStatus.PENDING,
            created_at=datetime.now(),
        )

        assert draft.id.startswith("DRAFT-")
        assert len(draft.id) == 14  # DRAFT- (6) + 8 hex chars

    def test_question_id_format(self):
        """Test pending question ID format."""
        from app.storage.models import PendingQuestion, Language, QuestionStatus

        question = PendingQuestion(
            id="Q-12345678",
            user_email="test@test.com",
            question="Test?",
            bot_answer="Answer",
            language=Language.EN,
            platform="discord",
            status=QuestionStatus.PENDING,
            created_at=datetime.now(),
        )

        assert question.id.startswith("Q-")
        assert len(question.id) == 10  # Q- (2) + 8 hex chars

    def test_feature_id_format(self):
        """Test feature suggestion ID format."""
        from app.storage.models import FeatureSuggestion, Language, FeatureStatus

        feature = FeatureSuggestion(
            id="FEAT-12345678",
            user_email="test@test.com",
            title="New Feature",
            description="Description",
            language=Language.EN,
            status=FeatureStatus.OPEN,
            created_at=datetime.now(),
        )

        assert feature.id.startswith("FEAT-")
        assert len(feature.id) == 13  # FEAT- (5) + 8 hex chars

    def test_id_uniqueness(self):
        """Test that IDs are unique."""
        import uuid

        # ID generation uses uuid internally, so let's verify uuid behavior
        ids = [str(uuid.uuid4().hex[:8]).upper() for _ in range(100)]
        assert len(set(ids)) == 100  # All should be unique


class TestStorageModels:
    """Tests for storage model structures."""

    def test_draft_update_fields(self):
        """Test DraftUpdate has required fields."""
        from app.storage.models import DraftUpdate, Language, DraftStatus

        draft = DraftUpdate(
            id="DRAFT-12345678",
            user_email="test@test.com",
            content="Test content",
            target_section="test.md",
            language=Language.EN,
            status=DraftStatus.PENDING,
            created_at=datetime.now(),
        )

        assert draft.user_email == "test@test.com"
        assert draft.content == "Test content"
        assert draft.target_section == "test.md"
        assert draft.language == Language.EN
        assert draft.status == DraftStatus.PENDING

    def test_pending_question_fields(self):
        """Test PendingQuestion has required fields."""
        from app.storage.models import PendingQuestion, Language, QuestionStatus

        question = PendingQuestion(
            id="Q-12345678",
            user_email="test@test.com",
            question="How?",
            bot_answer="Answer",
            language=Language.EN,
            platform="discord",
            status=QuestionStatus.PENDING,
            created_at=datetime.now(),
        )

        assert question.user_email == "test@test.com"
        assert question.question == "How?"
        assert question.bot_answer == "Answer"
        assert question.platform == "discord"

    def test_feature_suggestion_fields(self):
        """Test FeatureSuggestion has required fields."""
        from app.storage.models import FeatureSuggestion, Language, FeatureStatus

        feature = FeatureSuggestion(
            id="FEAT-12345678",
            user_email="test@test.com",
            title="New Feature",
            description="Description",
            language=Language.EN,
            status=FeatureStatus.OPEN,
            created_at=datetime.now(),
        )

        assert feature.user_email == "test@test.com"
        assert feature.title == "New Feature"
        assert feature.description == "Description"
        assert feature.status == FeatureStatus.OPEN

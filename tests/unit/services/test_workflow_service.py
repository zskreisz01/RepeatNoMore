"""Unit tests for workflow service."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.workflow_service import WorkflowService
from app.services.permission_service import PermissionService
from app.services.language_service import LanguageService
from app.services.git_service import GitService
from app.services.notification_service import NotificationService
from app.storage.repositories.draft_repository import DraftRepository
from app.storage.repositories.queue_repository import QueueRepository
from app.storage.repositories.feature_repository import FeatureRepository
from app.storage.models import DraftUpdate, PendingQuestion, FeatureSuggestion


class TestWorkflowService:
    """Tests for WorkflowService class."""

    @pytest.fixture
    def temp_storage(self, tmp_path: Path) -> dict:
        """Create temporary storage paths."""
        return {
            "drafts": str(tmp_path / "drafts.json"),
            "queue": str(tmp_path / "queue.json"),
            "features": str(tmp_path / "features.json"),
            "docs": str(tmp_path / "docs"),
        }

    @pytest.fixture
    def mock_notification(self) -> NotificationService:
        """Create a mock notification service."""
        service = MagicMock(spec=NotificationService)
        service.notify_question_escalated = AsyncMock(return_value={"discord": True, "teams": True})
        service.notify_draft_submitted = AsyncMock(return_value={"discord": True, "teams": True})
        return service

    @pytest.fixture
    def mock_git(self) -> GitService:
        """Create a mock git service."""
        service = MagicMock(spec=GitService)
        service.is_enabled.return_value = False
        service.sync_changes.return_value = {"success": True, "commit_sha": "abc123"}
        return service

    @pytest.fixture
    def service(
        self,
        temp_storage: dict,
        mock_notification: NotificationService,
        mock_git: GitService
    ) -> WorkflowService:
        """Create a workflow service instance with mocked dependencies."""
        # Create real repositories with temp paths
        draft_repo = DraftRepository(storage_path=temp_storage["drafts"])
        queue_repo = QueueRepository(storage_path=temp_storage["queue"])
        feature_repo = FeatureRepository(storage_path=temp_storage["features"])

        # Create permission and language services
        permission_service = PermissionService()
        language_service = LanguageService()

        # Patch the docs path
        with patch.object(language_service.settings, 'docs_repo_path', temp_storage["docs"]):
            return WorkflowService(
                permission_service=permission_service,
                language_service=language_service,
                git_service=mock_git,
                notification_service=mock_notification,
                draft_repository=draft_repo,
                queue_repository=queue_repo,
                feature_repository=feature_repo,
            )


class TestQAAcceptance:
    """Tests for Q&A acceptance workflow."""

    @pytest.fixture
    def service(self, tmp_path: Path) -> WorkflowService:
        """Create a workflow service instance."""
        draft_repo = DraftRepository(storage_path=str(tmp_path / "drafts.json"))
        queue_repo = QueueRepository(storage_path=str(tmp_path / "queue.json"))
        feature_repo = FeatureRepository(storage_path=str(tmp_path / "features.json"))
        notification = MagicMock(spec=NotificationService)
        notification.notify_question_escalated = AsyncMock()
        notification.notify_draft_submitted = AsyncMock()
        git = MagicMock(spec=GitService)
        git.is_enabled.return_value = False

        service = WorkflowService(
            draft_repository=draft_repo,
            queue_repository=queue_repo,
            feature_repository=feature_repo,
            notification_service=notification,
            git_service=git,
        )
        # Override language service paths
        service.language_service._settings = MagicMock()
        service.language_service._settings.docs_repo_path = str(tmp_path / "docs")

        return service

    @pytest.mark.asyncio
    async def test_accept_qa_creates_file(self, service: WorkflowService, tmp_path: Path):
        """Test accepting Q&A creates the Q&A file."""
        # Override the path method
        qa_file = tmp_path / "qa" / "accepted_qa_en.md"
        with patch.object(service.language_service, 'get_qa_file_path', return_value=qa_file):
            result = await service.accept_qa(
                question="How do I install?",
                answer="Run pip install.",
                user_email="user@example.com",
                language="en"
            )

        assert result["success"] is True
        assert "qa_id" in result
        assert qa_file.exists()

    @pytest.mark.asyncio
    async def test_accept_qa_appends_content(self, service: WorkflowService, tmp_path: Path):
        """Test Q&A content is appended to file."""
        qa_file = tmp_path / "qa" / "accepted_qa_en.md"
        with patch.object(service.language_service, 'get_qa_file_path', return_value=qa_file):
            await service.accept_qa(
                question="Question 1?",
                answer="Answer 1.",
                user_email="user@example.com"
            )
            await service.accept_qa(
                question="Question 2?",
                answer="Answer 2.",
                user_email="user@example.com"
            )

        content = qa_file.read_text()
        assert "Question 1?" in content
        assert "Answer 1." in content
        assert "Question 2?" in content
        assert "Answer 2." in content


class TestQAEscalation:
    """Tests for Q&A escalation workflow."""

    @pytest.fixture
    def service(self, tmp_path: Path) -> WorkflowService:
        """Create a workflow service instance."""
        draft_repo = DraftRepository(storage_path=str(tmp_path / "drafts.json"))
        queue_repo = QueueRepository(storage_path=str(tmp_path / "queue.json"))
        feature_repo = FeatureRepository(storage_path=str(tmp_path / "features.json"))
        notification = MagicMock(spec=NotificationService)
        notification.notify_question_escalated = AsyncMock(return_value={"discord": True})
        git = MagicMock(spec=GitService)

        return WorkflowService(
            draft_repository=draft_repo,
            queue_repository=queue_repo,
            feature_repository=feature_repo,
            notification_service=notification,
            git_service=git,
        )

    @pytest.mark.asyncio
    async def test_escalate_question(self, service: WorkflowService):
        """Test escalating a question."""
        result = await service.escalate_question(
            question="How do I configure X?",
            bot_answer="Configure it in settings.",
            user_email="user@example.com",
            rejection_reason="Answer was incomplete",
            platform="discord"
        )

        assert result["success"] is True
        assert "question_id" in result
        assert result["question_id"].startswith("Q-")

        # Verify notification was called
        service.notification_service.notify_question_escalated.assert_called_once()

    @pytest.mark.asyncio
    async def test_escalate_adds_to_queue(self, service: WorkflowService):
        """Test escalation adds question to queue."""
        await service.escalate_question(
            question="Test question?",
            bot_answer="Test answer.",
            user_email="user@example.com"
        )

        pending = service.get_pending_questions()
        assert len(pending) == 1
        assert pending[0].question == "Test question?"

    @pytest.mark.asyncio
    async def test_respond_to_question_requires_admin(self, service: WorkflowService):
        """Test responding requires admin permission."""
        result = await service.escalate_question(
            question="Test?",
            bot_answer="Answer.",
            user_email="user@example.com"
        )
        question_id = result["question_id"]

        with pytest.raises(PermissionError):
            await service.respond_to_question(
                question_id=question_id,
                admin_email="notadmin@example.com",
                response="Better answer."
            )

    @pytest.mark.asyncio
    async def test_respond_to_question_as_admin(self, service: WorkflowService):
        """Test admin can respond to question."""
        result = await service.escalate_question(
            question="Test?",
            bot_answer="Answer.",
            user_email="user@example.com"
        )
        question_id = result["question_id"]

        response = await service.respond_to_question(
            question_id=question_id,
            admin_email="admin@example.com",
            response="Better answer."
        )

        assert response["success"] is True


class TestFeatureSuggestion:
    """Tests for feature suggestion workflow."""

    @pytest.fixture
    def service(self, tmp_path: Path) -> WorkflowService:
        """Create a workflow service instance."""
        draft_repo = DraftRepository(storage_path=str(tmp_path / "drafts.json"))
        queue_repo = QueueRepository(storage_path=str(tmp_path / "queue.json"))
        feature_repo = FeatureRepository(storage_path=str(tmp_path / "features.json"))
        notification = MagicMock(spec=NotificationService)
        git = MagicMock(spec=GitService)

        service = WorkflowService(
            draft_repository=draft_repo,
            queue_repository=queue_repo,
            feature_repository=feature_repo,
            notification_service=notification,
            git_service=git,
        )
        return service

    @pytest.mark.asyncio
    async def test_suggest_feature(self, service: WorkflowService, tmp_path: Path):
        """Test suggesting a feature."""
        suggestions_file = tmp_path / "suggestions" / "suggested_features.md"
        with patch.object(service.language_service, 'get_suggestions_file_path', return_value=suggestions_file):
            result = await service.suggest_feature(
                title="PDF Export",
                description="Add ability to export docs as PDF",
                user_email="user@example.com"
            )

        assert result["success"] is True
        assert result["feature_id"].startswith("FEAT-")
        assert suggestions_file.exists()

    @pytest.mark.asyncio
    async def test_suggest_feature_saved_to_repo(self, service: WorkflowService, tmp_path: Path):
        """Test feature is saved to repository."""
        suggestions_file = tmp_path / "suggestions" / "suggested_features.md"
        with patch.object(service.language_service, 'get_suggestions_file_path', return_value=suggestions_file):
            await service.suggest_feature(
                title="Test Feature",
                description="Test description",
                user_email="user@example.com"
            )

        features = service.get_features()
        assert len(features) == 1
        assert features[0].title == "Test Feature"


class TestDraftWorkflow:
    """Tests for draft update workflow."""

    @pytest.fixture
    def service(self, tmp_path: Path) -> WorkflowService:
        """Create a workflow service instance."""
        draft_repo = DraftRepository(storage_path=str(tmp_path / "drafts.json"))
        queue_repo = QueueRepository(storage_path=str(tmp_path / "queue.json"))
        feature_repo = FeatureRepository(storage_path=str(tmp_path / "features.json"))
        notification = MagicMock(spec=NotificationService)
        notification.notify_draft_submitted = AsyncMock(return_value={"discord": True})
        git = MagicMock(spec=GitService)
        git.is_enabled.return_value = False

        return WorkflowService(
            draft_repository=draft_repo,
            queue_repository=queue_repo,
            feature_repository=feature_repo,
            notification_service=notification,
            git_service=git,
        )

    @pytest.mark.asyncio
    async def test_create_draft_update(self, service: WorkflowService, tmp_path: Path):
        """Test creating a draft update."""
        drafts_file = tmp_path / "drafts" / "draft_updates.md"
        with patch.object(service.language_service, 'get_drafts_file_path', return_value=drafts_file):
            result = await service.create_draft_update(
                content="New installation instructions.",
                target_section="getting_started.md#installation",
                user_email="user@example.com",
                description="Update installation section"
            )

        assert result["success"] is True
        assert result["draft_id"].startswith("DRAFT-")

    @pytest.mark.asyncio
    async def test_create_draft_notifies_admins(self, service: WorkflowService, tmp_path: Path):
        """Test draft creation notifies admins."""
        drafts_file = tmp_path / "drafts" / "draft_updates.md"
        with patch.object(service.language_service, 'get_drafts_file_path', return_value=drafts_file):
            await service.create_draft_update(
                content="Test content",
                target_section="test.md",
                user_email="user@example.com"
            )

        service.notification_service.notify_draft_submitted.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_drafts(self, service: WorkflowService, tmp_path: Path):
        """Test getting pending drafts."""
        drafts_file = tmp_path / "drafts" / "draft_updates.md"
        with patch.object(service.language_service, 'get_drafts_file_path', return_value=drafts_file):
            await service.create_draft_update(
                content="Test 1",
                target_section="test1.md",
                user_email="user@example.com"
            )
            await service.create_draft_update(
                content="Test 2",
                target_section="test2.md",
                user_email="user@example.com"
            )

        pending = service.get_pending_drafts()
        assert len(pending) == 2

    @pytest.mark.asyncio
    async def test_accept_draft_requires_admin(self, service: WorkflowService, tmp_path: Path):
        """Test accepting draft requires admin."""
        drafts_file = tmp_path / "drafts" / "draft_updates.md"
        with patch.object(service.language_service, 'get_drafts_file_path', return_value=drafts_file):
            result = await service.create_draft_update(
                content="Test",
                target_section="test.md",
                user_email="user@example.com"
            )

        with pytest.raises(PermissionError):
            await service.accept_draft(
                draft_id=result["draft_id"],
                admin_email="notadmin@example.com"
            )

    @pytest.mark.asyncio
    async def test_accept_draft_as_admin(self, service: WorkflowService, tmp_path: Path):
        """Test admin can accept draft."""
        drafts_file = tmp_path / "drafts" / "draft_updates.md"
        with patch.object(service.language_service, 'get_drafts_file_path', return_value=drafts_file):
            create_result = await service.create_draft_update(
                content="Test content",
                target_section="test.md",
                user_email="user@example.com"
            )

        # Mock the _apply_draft method
        with patch.object(service, '_apply_draft', new_callable=AsyncMock) as mock_apply:
            mock_apply.return_value = {"success": True, "file_path": "/path/to/file"}

            accept_result = await service.accept_draft(
                draft_id=create_result["draft_id"],
                admin_email="admin@example.com"
            )

        assert accept_result["success"] is True
        assert accept_result["approved"] is True

    @pytest.mark.asyncio
    async def test_reject_draft(self, service: WorkflowService, tmp_path: Path):
        """Test rejecting a draft."""
        drafts_file = tmp_path / "drafts" / "draft_updates.md"
        with patch.object(service.language_service, 'get_drafts_file_path', return_value=drafts_file):
            create_result = await service.create_draft_update(
                content="Test",
                target_section="test.md",
                user_email="user@example.com"
            )

        reject_result = await service.reject_draft(
            draft_id=create_result["draft_id"],
            admin_email="admin@example.com",
            reason="Content needs revision"
        )

        assert reject_result["success"] is True

        # Verify draft status
        drafts = service.get_drafts()
        assert drafts[0].status == "rejected"
        assert drafts[0].rejection_reason == "Content needs revision"


class TestGitSync:
    """Tests for git sync workflow."""

    @pytest.fixture
    def service(self, tmp_path: Path) -> WorkflowService:
        """Create a workflow service instance."""
        draft_repo = DraftRepository(storage_path=str(tmp_path / "drafts.json"))
        queue_repo = QueueRepository(storage_path=str(tmp_path / "queue.json"))
        feature_repo = FeatureRepository(storage_path=str(tmp_path / "features.json"))
        notification = MagicMock(spec=NotificationService)
        git = MagicMock(spec=GitService)

        return WorkflowService(
            draft_repository=draft_repo,
            queue_repository=queue_repo,
            feature_repository=feature_repo,
            notification_service=notification,
            git_service=git,
        )

    @pytest.mark.asyncio
    async def test_git_sync_requires_admin(self, service: WorkflowService):
        """Test git sync requires admin."""
        with pytest.raises(PermissionError):
            await service.git_sync(admin_email="notadmin@example.com")

    @pytest.mark.asyncio
    async def test_git_sync_when_disabled(self, service: WorkflowService):
        """Test git sync when disabled."""
        service.git_service.is_enabled.return_value = False

        result = await service.git_sync(admin_email="admin@example.com")

        assert result["success"] is False
        assert "disabled" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_git_sync_when_enabled(self, service: WorkflowService):
        """Test git sync when enabled."""
        service.git_service.is_enabled.return_value = True
        service.git_service.sync_changes.return_value = {
            "success": True,
            "commit_sha": "abc123",
            "pr_url": "https://example.com/pr/1"
        }

        result = await service.git_sync(admin_email="admin@example.com")

        assert result["success"] is True
        service.git_service.sync_changes.assert_called_once()

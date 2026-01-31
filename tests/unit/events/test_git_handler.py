"""Unit tests for GitHandler - git sync and action logging."""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import tempfile
import os

import pytest

from app.events.types import DocumentEvent, EventData
from app.events.handlers.git_handler import GitHandler


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings with temp log path."""
    settings = MagicMock()
    settings.docs_repo_path = str(tmp_path / "docs")
    settings.git_action_log_path = str(tmp_path / "logs" / "git_actions.log")
    return settings


@pytest.fixture
def mock_git_service():
    """Create mock git service."""
    service = MagicMock()
    service.is_enabled.return_value = True
    service.sync_changes.return_value = {
        "success": True,
        "commit_sha": "abc123def",
        "branch": "docs/draft-001",
        "pr_url": "https://dev.azure.com/pr/123",
    }
    return service


@pytest.fixture
def git_handler(mock_settings, mock_git_service):
    """Create GitHandler with mocked dependencies."""
    with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
         patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service), \
         patch("app.events.handlers.git_handler.get_event_dispatcher") as mock_dispatcher:
        mock_dispatcher.return_value.emit = AsyncMock()
        handler = GitHandler()
        return handler


class TestGitHandlerInitialization:
    """Tests for GitHandler initialization."""

    def test_init_creates_log_directory(self, mock_settings, mock_git_service):
        """Test that initialization creates the log directory."""
        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service):
            handler = GitHandler()

            log_dir = Path(mock_settings.git_action_log_path).parent
            assert log_dir.exists()


class TestGitHandlerEventHandling:
    """Tests for GitHandler event handling."""

    @pytest.mark.asyncio
    async def test_handles_draft_approved_event(self, git_handler, mock_git_service):
        """Test that DRAFT_APPROVED event triggers git sync."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_APPROVED,
            draft_id="DRAFT-001",
            file_path="/path/to/doc.md",
            user_email="admin@test.com",
            target_section="getting-started",
        )

        await git_handler.handle_event(event)

        mock_git_service.sync_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_question_answered_event(self, git_handler, mock_git_service):
        """Test that QUESTION_ANSWERED event triggers git sync."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_ANSWERED,
            question_id="Q-001",
            file_path="/path/to/qa.md",
            user_email="admin@test.com",
        )

        await git_handler.handle_event(event)

        mock_git_service.sync_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_doc_updated_event(self, git_handler, mock_git_service):
        """Test that DOC_UPDATED event triggers git sync."""
        event = EventData(
            event_type=DocumentEvent.DOC_UPDATED,
            file_path="/path/to/updated.md",
            user_email="user@test.com",
        )

        await git_handler.handle_event(event)

        mock_git_service.sync_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_git_sync_requested_event(self, git_handler, mock_git_service):
        """Test that GIT_SYNC_REQUESTED event triggers git sync."""
        event = EventData(
            event_type=DocumentEvent.GIT_SYNC_REQUESTED,
            user_email="admin@test.com",
            file_path="/path/to/doc.md",
        )

        await git_handler.handle_event(event)

        mock_git_service.sync_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_ignores_non_sync_events(self, git_handler, mock_git_service):
        """Test that non-sync events are ignored."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_CREATED,
            draft_id="DRAFT-001",
        )

        await git_handler.handle_event(event)

        mock_git_service.sync_changes.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_git_disabled(self, mock_settings):
        """Test that sync is skipped when git is disabled."""
        mock_git_service = MagicMock()
        mock_git_service.is_enabled.return_value = False

        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service):
            handler = GitHandler()

            event = EventData(
                event_type=DocumentEvent.DRAFT_APPROVED,
                file_path="/path/to/doc.md",
            )

            await handler.handle_event(event)

            mock_git_service.sync_changes.assert_not_called()


class TestGitHandlerActionLogging:
    """Tests for GitHandler file-based action logging."""

    @pytest.mark.asyncio
    async def test_logs_successful_sync_to_file(self, mock_settings, mock_git_service):
        """Test that successful sync is logged to file."""
        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service), \
             patch("app.events.handlers.git_handler.get_event_dispatcher") as mock_dispatcher:
            mock_dispatcher.return_value.emit = AsyncMock()
            handler = GitHandler()

            event = EventData(
                event_type=DocumentEvent.DRAFT_APPROVED,
                draft_id="DRAFT-001",
                file_path="/path/to/doc.md",
                user_email="admin@test.com",
            )

            await handler.handle_event(event)

            # Read the log file
            log_path = Path(mock_settings.git_action_log_path)
            assert log_path.exists()

            log_content = log_path.read_text()
            assert "[SUCCESS]" in log_content
            assert "action=sync" in log_content
            assert "event_type=draft.approved" in log_content
            assert "commit=abc123def" in log_content
            assert "user=admin@test.com" in log_content

    @pytest.mark.asyncio
    async def test_logs_failed_sync_to_file(self, mock_settings):
        """Test that failed sync is logged to file with error."""
        mock_git_service = MagicMock()
        mock_git_service.is_enabled.return_value = True
        mock_git_service.sync_changes.return_value = {
            "success": False,
            "error": "Permission denied: cannot push to remote",
        }

        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service):
            handler = GitHandler()

            event = EventData(
                event_type=DocumentEvent.DRAFT_APPROVED,
                draft_id="DRAFT-002",
                file_path="/path/to/doc.md",
                user_email="admin@test.com",
            )

            await handler.handle_event(event)

            # Read the log file
            log_path = Path(mock_settings.git_action_log_path)
            assert log_path.exists()

            log_content = log_path.read_text()
            assert "[FAILED]" in log_content
            assert "action=sync" in log_content
            assert "Permission denied" in log_content

    @pytest.mark.asyncio
    async def test_logs_exception_to_file(self, mock_settings):
        """Test that exceptions during sync are logged to file."""
        mock_git_service = MagicMock()
        mock_git_service.is_enabled.return_value = True
        mock_git_service.sync_changes.side_effect = Exception("Network error")

        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service):
            handler = GitHandler()

            event = EventData(
                event_type=DocumentEvent.DOC_UPDATED,
                file_path="/path/to/doc.md",
                user_email="user@test.com",
            )

            await handler.handle_event(event)

            # Read the log file
            log_path = Path(mock_settings.git_action_log_path)
            assert log_path.exists()

            log_content = log_path.read_text()
            assert "[FAILED]" in log_content
            assert "Network error" in log_content

    def test_log_entry_format(self, mock_settings, mock_git_service):
        """Test that log entries have correct format."""
        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service):
            handler = GitHandler()

            handler._log_git_action(
                action="sync",
                success=True,
                event_type="draft.approved",
                commit_sha="abc123",
                branch="docs/draft-001",
                files=["/path/to/file1.md", "/path/to/file2.md"],
                pr_url="https://example.com/pr/1",
                user_email="user@test.com",
            )

            log_path = Path(mock_settings.git_action_log_path)
            log_content = log_path.read_text()

            # Verify format elements
            assert "[SUCCESS]" in log_content
            assert "action=sync" in log_content
            assert "event_type=draft.approved" in log_content
            assert "user=user@test.com" in log_content
            assert "branch=docs/draft-001" in log_content
            assert "commit=abc123" in log_content
            assert "pr_url=https://example.com/pr/1" in log_content
            assert "files=" in log_content

    def test_log_truncates_many_files(self, mock_settings, mock_git_service):
        """Test that log truncates file list when many files."""
        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service):
            handler = GitHandler()

            files = [f"/path/to/file{i}.md" for i in range(10)]

            handler._log_git_action(
                action="sync",
                success=True,
                event_type="doc.updated",
                files=files,
            )

            log_path = Path(mock_settings.git_action_log_path)
            log_content = log_path.read_text()

            # Should show first 5 files and indicate more
            assert "...+5 more" in log_content


class TestGitHandlerCommitMessageGeneration:
    """Tests for commit message generation."""

    def test_draft_approved_commit_message(self, git_handler):
        """Test commit message for draft approved event."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_APPROVED,
            draft_id="DRAFT-001",
            target_section="architecture",
        )

        message = git_handler._generate_commit_message(event)

        assert "Apply approved draft DRAFT-001" in message
        assert "architecture" in message

    def test_question_answered_commit_message(self, git_handler):
        """Test commit message for question answered event."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_ANSWERED,
            question_id="Q-001",
        )

        message = git_handler._generate_commit_message(event)

        assert "Add answer for question Q-001" in message

    def test_doc_updated_commit_message(self, git_handler):
        """Test commit message for doc updated event."""
        event = EventData(
            event_type=DocumentEvent.DOC_UPDATED,
        )

        message = git_handler._generate_commit_message(event)

        assert "Update documentation" in message


class TestGitHandlerBranchNameGeneration:
    """Tests for branch name generation."""

    def test_draft_branch_name(self, git_handler):
        """Test branch name for draft event."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_APPROVED,
            draft_id="DRAFT-001",
        )

        branch = git_handler._generate_branch_name(event)

        assert branch == "docs/draft-draft-001"

    def test_question_branch_name(self, git_handler):
        """Test branch name for question event."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_ANSWERED,
            question_id="Q-001",
        )

        branch = git_handler._generate_branch_name(event)

        assert branch == "docs/qa-q-001"

    def test_default_branch_name_has_timestamp(self, git_handler):
        """Test default branch name includes timestamp."""
        event = EventData(
            event_type=DocumentEvent.DOC_UPDATED,
        )

        branch = git_handler._generate_branch_name(event)

        assert branch.startswith("docs/update-")
        # Should have format like docs/update-20240101-120000
        assert len(branch) > len("docs/update-")


class TestGitSyncCompletedEvent:
    """Tests for GIT_SYNC_COMPLETED event emission."""

    @pytest.mark.asyncio
    async def test_emits_git_sync_completed_on_success(self, mock_settings, mock_git_service):
        """Test that GIT_SYNC_COMPLETED event is emitted on successful sync."""
        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service), \
             patch("app.events.handlers.git_handler.get_event_dispatcher") as mock_dispatcher:
            mock_emit = AsyncMock()
            mock_dispatcher.return_value.emit = mock_emit

            handler = GitHandler()

            event = EventData(
                event_type=DocumentEvent.DRAFT_APPROVED,
                draft_id="DRAFT-001",
                file_path="/path/to/doc.md",
                user_email="admin@test.com",
            )

            await handler.handle_event(event)

            # Verify GIT_SYNC_COMPLETED was emitted
            mock_emit.assert_called_once()
            emitted_event = mock_emit.call_args[0][0]
            assert emitted_event.event_type == DocumentEvent.GIT_SYNC_COMPLETED
            assert emitted_event.commit_sha == "abc123def"
            assert emitted_event.branch_name == "docs/draft-001"

    @pytest.mark.asyncio
    async def test_does_not_emit_on_failure(self, mock_settings):
        """Test that GIT_SYNC_COMPLETED event is not emitted on failure."""
        mock_git_service = MagicMock()
        mock_git_service.is_enabled.return_value = True
        mock_git_service.sync_changes.return_value = {"success": False, "error": "Failed"}

        with patch("app.events.handlers.git_handler.get_settings", return_value=mock_settings), \
             patch("app.events.handlers.git_handler.get_git_service", return_value=mock_git_service), \
             patch("app.events.handlers.git_handler.get_event_dispatcher") as mock_dispatcher:
            mock_emit = AsyncMock()
            mock_dispatcher.return_value.emit = mock_emit

            handler = GitHandler()

            event = EventData(
                event_type=DocumentEvent.DRAFT_APPROVED,
                draft_id="DRAFT-001",
                file_path="/path/to/doc.md",
            )

            await handler.handle_event(event)

            # Verify GIT_SYNC_COMPLETED was NOT emitted
            mock_emit.assert_not_called()

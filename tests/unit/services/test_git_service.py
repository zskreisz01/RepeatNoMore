"""Unit tests for Git service."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestLocalGitProvider:
    """Tests for LocalGitProvider."""

    @pytest.fixture
    def local_provider(self):
        """Create a LocalGitProvider instance."""
        from app.services.git_service import LocalGitProvider
        return LocalGitProvider(repo_path="/tmp/test_repo")

    def test_init(self, local_provider):
        """Test initialization."""
        assert local_provider.repo_path == Path("/tmp/test_repo")

    def test_create_branch(self, local_provider):
        """Test branch creation."""
        with patch.object(local_provider, "_run_git") as mock_run:
            mock_run.return_value = (True, "Switched to new branch")

            result = local_provider.create_branch("test-branch")

            # Should be called for checkout and then create
            assert mock_run.called
            assert result is True

    def test_create_branch_failure(self, local_provider):
        """Test branch creation failure."""
        with patch.object(local_provider, "_run_git") as mock_run:
            mock_run.return_value = (False, "Error")

            result = local_provider.create_branch("test-branch")

            assert result is False

    def test_commit(self, local_provider):
        """Test committing changes."""
        with patch.object(local_provider, "_run_git") as mock_run:
            # First call for add, second for commit, third for rev-parse
            mock_run.side_effect = [
                (True, ""),  # git add
                (True, ""),  # git commit
                (True, "abc123")  # git rev-parse
            ]

            result = local_provider.commit("Test commit message", ["file1.txt"])

            assert result == "abc123"

    def test_push(self, local_provider):
        """Test pushing to remote."""
        with patch.object(local_provider, "_run_git") as mock_run:
            mock_run.return_value = (True, "")

            result = local_provider.push()

            mock_run.assert_called()
            assert result is True

    def test_push_with_branch(self, local_provider):
        """Test pushing specific branch."""
        with patch.object(local_provider, "_run_git") as mock_run:
            mock_run.return_value = (True, "")

            result = local_provider.push(branch="feature-branch")

            assert result is True

    def test_get_current_branch(self, local_provider):
        """Test getting current branch."""
        with patch.object(local_provider, "_run_git") as mock_run:
            mock_run.return_value = (True, "main")

            result = local_provider.get_current_branch()

            assert result == "main"

    def test_run_git_command(self, local_provider):
        """Test _run_git executes commands."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr=""
            )

            success, output = local_provider._run_git("status")

            assert success is True
            assert output == "output"
            mock_run.assert_called_once()


class TestAzureDevOpsGitProvider:
    """Tests for AzureDevOpsGitProvider."""

    @pytest.fixture
    def azure_provider(self):
        """Create an AzureDevOpsGitProvider instance."""
        from app.services.git_service import AzureDevOpsGitProvider
        return AzureDevOpsGitProvider(
            organization="test-org",
            project="test-project",
            repository="test-repo",
            pat="test-pat-token"
        )

    def test_init(self, azure_provider):
        """Test initialization."""
        assert azure_provider.organization == "test-org"
        assert azure_provider.project == "test-project"
        assert azure_provider.repository == "test-repo"

    def test_base_url(self, azure_provider):
        """Test base URL construction."""
        expected = "https://dev.azure.com/test-org/test-project/_apis/git/repositories/test-repo"
        assert azure_provider.base_url == expected

    def test_headers_contain_auth(self, azure_provider):
        """Test that headers contain authorization."""
        headers = azure_provider.headers
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")


class TestGitService:
    """Tests for GitService."""

    def test_service_init(self):
        """Test GitService initialization."""
        with patch("app.services.git_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                docs_git_enabled=True,
                docs_repo_path="/tmp/test_docs",
                azure_devops_organization=None,
            )
            from app.services.git_service import GitService
            service = GitService()
            assert service.settings is not None

    def test_is_enabled_when_true(self):
        """Test is_enabled when local git is enabled."""
        with patch("app.services.git_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                docs_git_enabled=True,
                docs_repo_path="/tmp/test_docs",
            )
            from app.services.git_service import GitService
            service = GitService()
            assert service.is_enabled() is True

    def test_is_enabled_when_false(self):
        """Test is_enabled when git is disabled."""
        with patch("app.services.git_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                docs_git_enabled=False,
            )
            from app.services.git_service import GitService
            service = GitService()
            assert service.is_enabled() is False


class TestGitBranchNaming:
    """Tests for git branch naming conventions."""

    def test_branch_name_format(self):
        """Test branch name format generation."""
        import re
        from datetime import datetime

        # Generate a branch name following the pattern
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"docs/update-{timestamp}"

        # Verify pattern
        pattern = r"^docs/update-\d{8}-\d{6}$"
        assert re.match(pattern, branch_name)

    def test_branch_name_sanitization(self):
        """Test that branch names are properly sanitized."""
        # Invalid characters should be removed
        invalid_chars = ["~", "^", ":", "?", "*", "[", "\\", " "]

        for char in invalid_chars:
            test_name = f"docs/update{char}test"
            sanitized = test_name.replace(char, "-")
            assert char not in sanitized

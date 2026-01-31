"""Git service for repository operations with Azure DevOps integration."""

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Optional
import subprocess
import base64
import json

import httpx

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GitProvider(ABC):
    """Abstract base class for git providers."""

    @abstractmethod
    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch."""
        pass

    @abstractmethod
    def commit(self, message: str, files: list[str]) -> Optional[str]:
        """Commit changes and return commit SHA."""
        pass

    @abstractmethod
    def push(self, branch: Optional[str] = None) -> bool:
        """Push changes to remote."""
        pass

    @abstractmethod
    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str = "main"
    ) -> Optional[str]:
        """Create a pull request and return URL."""
        pass

    @abstractmethod
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        pass


class LocalGitProvider(GitProvider):
    """Local git operations using subprocess."""

    def __init__(self, repo_path: str):
        """
        Initialize local git provider.

        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path)
        logger.info("local_git_provider_initialized", repo_path=str(repo_path))

    def _run_git(self, *args: str) -> tuple[bool, str]:
        """
        Run a git command.

        Args:
            args: Git command arguments

        Returns:
            Tuple of (success, output)
        """
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.error("git_command_timeout", args=args)
            return False, "Command timed out"
        except Exception as e:
            logger.error("git_command_error", args=args, error=str(e))
            return False, str(e)

    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch."""
        # Checkout base branch first
        success, _ = self._run_git("checkout", from_branch)
        if not success:
            return False

        # Create and checkout new branch
        success, output = self._run_git("checkout", "-b", branch_name)
        if success:
            logger.info("branch_created", branch=branch_name)
        return success

    def commit(self, message: str, files: list[str]) -> Optional[str]:
        """Commit changes and return commit SHA."""
        # Stage files
        for file_path in files:
            success, _ = self._run_git("add", file_path)
            if not success:
                logger.warning("git_add_failed", file=file_path)

        # Commit
        success, output = self._run_git("commit", "-m", message)
        if not success:
            if "nothing to commit" in output:
                logger.info("nothing_to_commit")
                return None
            logger.error("commit_failed", output=output)
            return None

        # Get commit SHA
        success, sha = self._run_git("rev-parse", "HEAD")
        if success:
            logger.info("commit_created", sha=sha[:8])
            return sha
        return None

    def push(self, branch: Optional[str] = None) -> bool:
        """Push changes to remote."""
        if branch:
            success, output = self._run_git("push", "-u", "origin", branch)
        else:
            success, output = self._run_git("push")

        if success:
            logger.info("push_successful", branch=branch)
        else:
            logger.error("push_failed", output=output)
        return success

    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str = "main"
    ) -> Optional[str]:
        """Create a pull request (not supported for local git)."""
        logger.warning(
            "pr_creation_not_supported",
            provider="local",
            message="Use Azure DevOps or GitHub CLI for PR creation"
        )
        return None

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        success, branch = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        return branch if success else "unknown"


class SSHGitProvider(GitProvider):
    """Git operations over SSH with key-based authentication."""

    def __init__(
        self,
        repo_path: str,
        ssh_url: str,
        ssh_key_path: str,
        remote_name: str = "origin"
    ):
        """
        Initialize SSH git provider.

        Args:
            repo_path: Path to the local git repository
            ssh_url: SSH URL for the remote repository
            ssh_key_path: Path to the SSH private key
            remote_name: Name of the git remote (default: origin)
        """
        self.repo_path = Path(repo_path)
        self.ssh_url = ssh_url
        self.ssh_key_path = Path(ssh_key_path)
        self.remote_name = remote_name

        # Construct GIT_SSH_COMMAND for key-based auth
        self.git_ssh_command = (
            f"ssh -i {self.ssh_key_path} "
            f"-o StrictHostKeyChecking=no "
            f"-o UserKnownHostsFile=/dev/null"
        )

        logger.info(
            "ssh_git_provider_initialized",
            repo_path=str(repo_path),
            ssh_url=ssh_url,
        )

    def _run_git(self, *args: str, use_ssh: bool = False) -> tuple[bool, str]:
        """
        Run a git command.

        Args:
            args: Git command arguments
            use_ssh: Whether to use SSH environment for this command

        Returns:
            Tuple of (success, output)
        """
        env = None
        if use_ssh:
            import os
            env = os.environ.copy()
            env["GIT_SSH_COMMAND"] = self.git_ssh_command

        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=120,
                env=env
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.error("git_command_timeout", args=args)
            return False, "Command timed out"
        except Exception as e:
            logger.error("git_command_error", args=args, error=str(e))
            return False, str(e)

    def _ensure_remote(self) -> bool:
        """Ensure the SSH remote is configured."""
        # Check if remote exists
        success, remotes = self._run_git("remote", "-v")
        if self.remote_name in remotes:
            # Update remote URL to SSH
            success, output = self._run_git(
                "remote", "set-url", self.remote_name, self.ssh_url
            )
        else:
            # Add remote
            success, output = self._run_git(
                "remote", "add", self.remote_name, self.ssh_url
            )

        if success:
            logger.debug("ssh_remote_configured", remote=self.remote_name)
        else:
            logger.warning("ssh_remote_config_failed", output=output)
        return success

    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch."""
        # Fetch latest from remote first
        self._ensure_remote()
        self._run_git("fetch", self.remote_name, use_ssh=True)

        # Try to checkout base branch
        success, _ = self._run_git("checkout", from_branch)
        if not success:
            # Try remote branch
            success, _ = self._run_git("checkout", "-b", from_branch, f"{self.remote_name}/{from_branch}")

        if not success:
            logger.warning("base_branch_checkout_failed", branch=from_branch)
            return False

        # Create and checkout new branch
        success, output = self._run_git("checkout", "-b", branch_name)
        if success:
            logger.info("branch_created", branch=branch_name)
        else:
            logger.error("branch_creation_failed", branch=branch_name, output=output)
        return success

    def commit(self, message: str, files: list[str]) -> Optional[str]:
        """Commit changes and return commit SHA."""
        # Stage files
        for file_path in files:
            success, _ = self._run_git("add", file_path)
            if not success:
                logger.warning("git_add_failed", file=file_path)

        # Commit
        success, output = self._run_git("commit", "-m", message)
        if not success:
            if "nothing to commit" in output:
                logger.info("nothing_to_commit")
                return None
            logger.error("commit_failed", output=output)
            return None

        # Get commit SHA
        success, sha = self._run_git("rev-parse", "HEAD")
        if success:
            logger.info("commit_created", sha=sha[:8])
            return sha
        return None

    def push(self, branch: Optional[str] = None) -> bool:
        """Push changes to remote over SSH."""
        self._ensure_remote()

        if branch:
            success, output = self._run_git(
                "push", "-u", self.remote_name, branch, use_ssh=True
            )
        else:
            success, output = self._run_git("push", use_ssh=True)

        if success:
            logger.info("push_successful", branch=branch)
        else:
            logger.error("push_failed", output=output)
        return success

    def pull(self, branch: Optional[str] = None) -> bool:
        """Pull changes from remote over SSH."""
        self._ensure_remote()

        if branch:
            success, output = self._run_git(
                "pull", self.remote_name, branch, use_ssh=True
            )
        else:
            success, output = self._run_git("pull", use_ssh=True)

        if success:
            logger.info("pull_successful", branch=branch)
        else:
            logger.error("pull_failed", output=output)
        return success

    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str = "main"
    ) -> Optional[str]:
        """
        Create a pull request.

        Note: SSH provider doesn't support PR creation directly.
        Use Azure DevOps REST API separately if needed.
        """
        logger.warning(
            "pr_creation_not_supported_via_ssh",
            message="Use Azure DevOps API or CLI for PR creation"
        )
        return None

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        success, branch = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        return branch if success else "unknown"

    def clone(self, target_path: Optional[str] = None) -> bool:
        """
        Clone the repository via SSH.

        Args:
            target_path: Optional target directory. Uses repo_path if not specified.

        Returns:
            True if successful
        """
        target = target_path or str(self.repo_path)
        success, output = self._run_git(
            "clone", self.ssh_url, target, use_ssh=True
        )
        if success:
            logger.info("clone_successful", target=target)
        else:
            logger.error("clone_failed", output=output)
        return success


class AzureDevOpsGitProvider(GitProvider):
    """Azure DevOps git operations via REST API."""

    def __init__(
        self,
        organization: str,
        project: str,
        repository: str,
        pat: str,
        local_repo_path: Optional[str] = None
    ):
        """
        Initialize Azure DevOps git provider.

        Args:
            organization: Azure DevOps organization name
            project: Project name
            repository: Repository name
            pat: Personal Access Token
            local_repo_path: Optional local repository path for file operations
        """
        self.organization = organization
        self.project = project
        self.repository = repository
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis/git/repositories/{repository}"
        self.auth_header = base64.b64encode(f":{pat}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json"
        }
        self.local_provider = LocalGitProvider(local_repo_path) if local_repo_path else None
        logger.info(
            "azure_devops_provider_initialized",
            organization=organization,
            project=project,
            repository=repository
        )

    def _api_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        api_version: str = "7.0"
    ) -> tuple[bool, dict]:
        """
        Make an API request to Azure DevOps.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            api_version: API version

        Returns:
            Tuple of (success, response_data)
        """
        url = f"{self.base_url}/{endpoint}?api-version={api_version}"
        try:
            with httpx.Client() as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    timeout=30.0
                )
                if response.status_code >= 400:
                    logger.error(
                        "azure_devops_api_error",
                        status=response.status_code,
                        body=response.text[:500]
                    )
                    return False, {"error": response.text}
                return True, response.json() if response.text else {}
        except Exception as e:
            logger.error("azure_devops_api_exception", error=str(e))
            return False, {"error": str(e)}

    def create_branch(self, branch_name: str, from_branch: str = "main") -> bool:
        """Create a new branch via local git."""
        if self.local_provider:
            return self.local_provider.create_branch(branch_name, from_branch)
        logger.warning("no_local_repo_for_branch_creation")
        return False

    def commit(self, message: str, files: list[str]) -> Optional[str]:
        """Commit changes via local git."""
        if self.local_provider:
            return self.local_provider.commit(message, files)
        logger.warning("no_local_repo_for_commit")
        return None

    def push(self, branch: Optional[str] = None) -> bool:
        """Push changes via local git."""
        if self.local_provider:
            return self.local_provider.push(branch)
        logger.warning("no_local_repo_for_push")
        return False

    def create_pull_request(
        self,
        title: str,
        description: str,
        source_branch: str,
        target_branch: str = "main"
    ) -> Optional[str]:
        """Create a pull request via Azure DevOps API."""
        data = {
            "sourceRefName": f"refs/heads/{source_branch}",
            "targetRefName": f"refs/heads/{target_branch}",
            "title": title,
            "description": description
        }

        success, response = self._api_request("POST", "pullrequests", data)
        if success and "pullRequestId" in response:
            pr_id = response["pullRequestId"]
            pr_url = f"https://dev.azure.com/{self.organization}/{self.project}/_git/{self.repository}/pullrequest/{pr_id}"
            logger.info("pr_created", pr_id=pr_id, url=pr_url)
            return pr_url

        logger.error("pr_creation_failed", response=response)
        return None

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        if self.local_provider:
            return self.local_provider.get_current_branch()
        return "unknown"


class GitService:
    """Service for git operations."""

    def __init__(self):
        """Initialize git service."""
        self.settings = get_settings()
        self._provider: Optional[GitProvider] = None
        logger.info("git_service_initialized")

    @property
    def provider(self) -> GitProvider:
        """Get or create git provider."""
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    def _create_provider(self) -> GitProvider:
        """Create the appropriate git provider based on configuration."""
        settings = self.settings

        # Check if SSH is configured (preferred method)
        if (
            hasattr(settings, 'azure_devops_ssh_url') and
            settings.azure_devops_ssh_url and
            hasattr(settings, 'azure_devops_ssh_key_path') and
            settings.azure_devops_ssh_key_path
        ):
            logger.info("using_ssh_git_provider")
            return SSHGitProvider(
                repo_path=settings.docs_repo_path,
                ssh_url=settings.azure_devops_ssh_url,
                ssh_key_path=settings.azure_devops_ssh_key_path,
            )

        # Check if Azure DevOps PAT is configured (fallback)
        if (
            hasattr(settings, 'azure_devops_organization') and
            settings.azure_devops_organization and
            hasattr(settings, 'azure_devops_pat') and
            settings.azure_devops_pat
        ):
            logger.info("using_azure_devops_git_provider")
            return AzureDevOpsGitProvider(
                organization=settings.azure_devops_organization,
                project=getattr(settings, 'azure_devops_project', ''),
                repository=getattr(settings, 'azure_devops_repo', ''),
                pat=settings.azure_devops_pat,
                local_repo_path=settings.docs_repo_path
            )

        # Default to local git
        logger.info("using_local_git_provider")
        return LocalGitProvider(settings.docs_repo_path)

    def is_enabled(self) -> bool:
        """Check if git operations are enabled."""
        return self.settings.docs_git_enabled

    def sync_changes(
        self,
        files: list[str],
        commit_message: str,
        branch_name: Optional[str] = None,
        create_pr: bool = True
    ) -> dict:
        """
        Sync changes to git repository.

        Args:
            files: List of file paths to commit
            commit_message: Commit message
            branch_name: Optional branch name (creates new branch if provided)
            create_pr: Whether to create a pull request

        Returns:
            Dictionary with sync results
        """
        if not self.is_enabled():
            return {
                "success": False,
                "error": "Git operations are disabled",
                "branch": None,
                "commit_sha": None,
                "pr_url": None
            }

        result = {
            "success": False,
            "branch": branch_name or self.provider.get_current_branch(),
            "commit_sha": None,
            "pr_url": None
        }

        # Create branch if specified
        if branch_name:
            if not self.provider.create_branch(branch_name):
                result["error"] = f"Failed to create branch {branch_name}"
                return result

        # Commit changes
        commit_sha = self.provider.commit(commit_message, files)
        if not commit_sha:
            result["error"] = "Failed to commit changes"
            return result

        result["commit_sha"] = commit_sha

        # Push changes
        if not self.provider.push(branch_name):
            result["error"] = "Failed to push changes"
            return result

        # Create PR if requested and on a feature branch
        if create_pr and branch_name:
            pr_url = self.provider.create_pull_request(
                title=commit_message.split('\n')[0][:80],
                description=commit_message,
                source_branch=branch_name,
                target_branch=self.settings.docs_git_branch
            )
            result["pr_url"] = pr_url

        result["success"] = True
        logger.info(
            "git_sync_complete",
            branch=result["branch"],
            commit=commit_sha[:8] if commit_sha else None,
            pr_url=result["pr_url"]
        )

        return result


# Global instance
_git_service: Optional[GitService] = None


@lru_cache()
def get_git_service() -> GitService:
    """
    Get or create a global git service instance.

    Returns:
        GitService: The git service
    """
    global _git_service
    if _git_service is None:
        _git_service = GitService()
    return _git_service

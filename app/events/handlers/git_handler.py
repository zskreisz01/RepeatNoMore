"""Git sync handler for document events."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.events.types import DocumentEvent, EventData
from app.events import get_event_dispatcher
from app.services.git_service import get_git_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GitHandler:
    """
    Handler for syncing document changes to git via SSH.

    Commits and pushes changes to the configured Azure DevOps repository
    when relevant document events occur. Logs all git actions to a file.
    """

    def __init__(self):
        """Initialize the git handler."""
        self.settings = get_settings()
        self.git_service = get_git_service()
        self._ensure_log_file()
        logger.info("git_handler_initialized")

    def _ensure_log_file(self) -> None:
        """Ensure the git action log file directory exists."""
        log_path = Path(self.settings.git_action_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_git_action(
        self,
        action: str,
        success: bool,
        event_type: str,
        commit_sha: Optional[str] = None,
        branch: Optional[str] = None,
        files: Optional[list[str]] = None,
        error: Optional[str] = None,
        pr_url: Optional[str] = None,
        user_email: Optional[str] = None,
    ) -> None:
        """
        Log a git action to the git actions log file.

        Args:
            action: The action performed (sync, commit, push, etc.)
            success: Whether the action was successful
            event_type: The event type that triggered the action
            commit_sha: The commit SHA if available
            branch: The branch name
            files: List of files affected
            error: Error message if the action failed
            pr_url: PR URL if one was created
            user_email: User who triggered the action
        """
        try:
            log_path = Path(self.settings.git_action_log_path)
            timestamp = datetime.utcnow().isoformat()
            status = "SUCCESS" if success else "FAILED"

            log_entry = (
                f"[{timestamp}] [{status}] action={action} "
                f"event_type={event_type}"
            )

            if user_email:
                log_entry += f" user={user_email}"
            if branch:
                log_entry += f" branch={branch}"
            if commit_sha:
                log_entry += f" commit={commit_sha}"
            if pr_url:
                log_entry += f" pr_url={pr_url}"
            if files:
                log_entry += f" files={','.join(files[:5])}"
                if len(files) > 5:
                    log_entry += f"...+{len(files)-5} more"
            if error:
                log_entry += f" error=\"{error}\""

            log_entry += "\n"

            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)

            logger.debug(
                "git_action_logged",
                action=action,
                success=success,
                log_path=str(log_path),
            )

        except Exception as e:
            logger.error(
                "git_action_logging_failed",
                error=str(e),
            )

    async def handle_event(self, event: EventData) -> None:
        """
        Handle document-related events that require git sync.

        Args:
            event: The event data
        """
        # Only handle events that should trigger git sync
        sync_events = [
            DocumentEvent.DRAFT_APPROVED,
            DocumentEvent.QUESTION_ANSWERED,
            DocumentEvent.DOC_UPDATED,
            DocumentEvent.GIT_SYNC_REQUESTED,
        ]

        if event.event_type not in sync_events:
            return

        if not self.git_service.is_enabled():
            logger.debug("git_sync_disabled")
            return

        await self._sync_changes(event)

    async def _sync_changes(self, event: EventData) -> None:
        """
        Commit and push changes to git.

        Args:
            event: The event data containing file information
        """
        files = []
        branch_name = None
        commit_message = None

        try:
            # Determine commit message based on event type
            commit_message = self._generate_commit_message(event)

            # Determine files to sync
            if event.file_path:
                files.append(event.file_path)

            # Add mkdocs.yml if it might have been updated
            if event.event_type in [
                DocumentEvent.DRAFT_APPROVED,
                DocumentEvent.QUESTION_ANSWERED,
            ]:
                mkdocs_path = self._get_mkdocs_path()
                if mkdocs_path:
                    files.append(mkdocs_path)

            if not files:
                logger.debug("no_files_to_sync", event_type=event.event_type.value)
                return

            # Generate branch name
            branch_name = self._generate_branch_name(event)

            # Sync changes via git service
            result = self.git_service.sync_changes(
                files=files,
                commit_message=commit_message,
                branch_name=branch_name,
                create_pr=True,
            )

            if result.get("success"):
                logger.info(
                    "git_sync_completed",
                    event_type=event.event_type.value,
                    commit_sha=result.get("commit_sha"),
                    branch=result.get("branch"),
                )

                # Log successful git action
                self._log_git_action(
                    action="sync",
                    success=True,
                    event_type=event.event_type.value,
                    commit_sha=result.get("commit_sha"),
                    branch=result.get("branch"),
                    files=files,
                    pr_url=result.get("pr_url"),
                    user_email=event.user_email,
                )

                # Emit GIT_SYNC_COMPLETED event
                dispatcher = get_event_dispatcher()
                await dispatcher.emit(EventData(
                    event_type=DocumentEvent.GIT_SYNC_COMPLETED,
                    source="git_handler",
                    user_email=event.user_email,
                    commit_sha=result.get("commit_sha"),
                    branch_name=result.get("branch"),
                    file_path=event.file_path,
                    metadata={
                        "pr_url": result.get("pr_url"),
                        "original_event": event.event_type.value,
                    },
                ))
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(
                    "git_sync_failed",
                    event_type=event.event_type.value,
                    error=error_msg,
                )

                # Log failed git action
                self._log_git_action(
                    action="sync",
                    success=False,
                    event_type=event.event_type.value,
                    branch=branch_name,
                    files=files,
                    error=error_msg,
                    user_email=event.user_email,
                )

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "git_sync_exception",
                event_type=event.event_type.value,
                error=error_msg,
            )

            # Log exception as failed git action
            self._log_git_action(
                action="sync",
                success=False,
                event_type=event.event_type.value,
                branch=branch_name,
                files=files if files else None,
                error=error_msg,
                user_email=event.user_email,
            )

    def _generate_commit_message(self, event: EventData) -> str:
        """Generate an appropriate commit message based on event type."""
        messages = {
            DocumentEvent.DRAFT_APPROVED: f"docs: Apply approved draft {event.draft_id or 'unknown'}",
            DocumentEvent.QUESTION_ANSWERED: f"docs: Add answer for question {event.question_id or 'unknown'}",
            DocumentEvent.DOC_UPDATED: "docs: Update documentation",
            DocumentEvent.GIT_SYNC_REQUESTED: f"docs: Manual sync requested by {event.user_email or 'system'}",
        }
        base_message = messages.get(event.event_type, "docs: Update documentation")

        # Add description if available
        if event.target_section:
            base_message += f" - {event.target_section}"

        return base_message

    def _generate_branch_name(self, event: EventData) -> Optional[str]:
        """Generate a branch name for the sync operation."""
        if event.draft_id:
            return f"docs/draft-{event.draft_id.lower()}"
        elif event.question_id:
            return f"docs/qa-{event.question_id.lower()}"
        else:
            timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            return f"docs/update-{timestamp}"

    def _get_mkdocs_path(self) -> Optional[str]:
        """Get the path to mkdocs.yml."""
        base_path = Path(self.settings.docs_repo_path)
        mkdocs_path = base_path / "mkdocs.yml"
        if mkdocs_path.exists():
            return str(mkdocs_path)
        return None

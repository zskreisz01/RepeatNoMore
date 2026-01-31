"""Permission service for user authorization management."""

from functools import lru_cache
from typing import Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Admin users - configure via environment variable DISCORD_ADMIN_USERNAMES
# or replace these defaults with your own admin emails
DEFAULT_ADMIN_EMAILS = [
    "admin@example.com",
]

# Discord admin usernames (will be converted to username@discord.user)
# Configure via environment variable DISCORD_ADMIN_USERNAMES
DEFAULT_DISCORD_ADMINS = [
    "your_admin_username",
]


class PermissionService:
    """Service for managing user permissions and authorization."""

    def __init__(self, admin_emails: Optional[list[str]] = None):
        """
        Initialize permission service.

        Args:
            admin_emails: Optional list of admin email addresses.
                         Defaults to the predefined admin list.
        """
        self.settings = get_settings()
        self._admin_emails = [
            email.lower() for email in (admin_emails or DEFAULT_ADMIN_EMAILS)
        ]

        # Add Discord admin usernames (converted to username@discord.user format)
        discord_admins = getattr(self.settings, 'discord_admin_usernames', None)
        if discord_admins:
            # From environment variable (comma-separated)
            discord_usernames = [u.strip().lower() for u in discord_admins.split(",") if u.strip()]
        else:
            # Use defaults
            discord_usernames = [u.lower() for u in DEFAULT_DISCORD_ADMINS]

        # Add Discord admin emails to the admin list
        for username in discord_usernames:
            discord_email = f"{username}@discord.user"
            if discord_email not in self._admin_emails:
                self._admin_emails.append(discord_email)

        logger.info(
            "permission_service_initialized",
            admin_count=len(self._admin_emails),
            discord_admins=discord_usernames
        )

    @property
    def admin_emails(self) -> list[str]:
        """Get the list of admin email addresses."""
        return self._admin_emails.copy()

    def add_admin(self, email: str) -> None:
        """
        Add a new admin email.

        Args:
            email: Email address to add as admin
        """
        email_lower = email.lower()
        if email_lower not in self._admin_emails:
            self._admin_emails.append(email_lower)
            logger.info("admin_added", email=email_lower)

    def remove_admin(self, email: str) -> bool:
        """
        Remove an admin email.

        Args:
            email: Email address to remove

        Returns:
            True if removed, False if not found
        """
        email_lower = email.lower()
        if email_lower in self._admin_emails:
            self._admin_emails.remove(email_lower)
            logger.info("admin_removed", email=email_lower)
            return True
        return False

    def is_admin(self, user_email: str) -> bool:
        """
        Check if a user is an admin.

        Args:
            user_email: User's email address

        Returns:
            True if the user is an admin
        """
        is_admin = user_email.lower() in self._admin_emails
        logger.debug("permission_check", email=user_email, is_admin=is_admin)
        return is_admin

    def can_approve_docs(self, user_email: str) -> bool:
        """
        Check if user can approve documentation updates.

        Args:
            user_email: User's email address

        Returns:
            True if user can approve docs
        """
        return self.is_admin(user_email)

    def can_edit_docs(self, user_email: str) -> bool:
        """
        Check if user can directly edit documentation.

        Args:
            user_email: User's email address

        Returns:
            True if user can edit docs
        """
        return self.is_admin(user_email)

    def can_accept_drafts(self, user_email: str) -> bool:
        """
        Check if user can accept draft updates.

        Args:
            user_email: User's email address

        Returns:
            True if user can accept drafts
        """
        return self.is_admin(user_email)

    def can_git_sync(self, user_email: str) -> bool:
        """
        Check if user can trigger git sync operations.

        Args:
            user_email: User's email address

        Returns:
            True if user can trigger git sync
        """
        return self.is_admin(user_email)

    def can_respond_to_queue(self, user_email: str) -> bool:
        """
        Check if user can respond to pending question queue.

        Args:
            user_email: User's email address

        Returns:
            True if user can respond to queue
        """
        return self.is_admin(user_email)

    def can_view_admin_dashboard(self, user_email: str) -> bool:
        """
        Check if user can view admin dashboard/pending items.

        Args:
            user_email: User's email address

        Returns:
            True if user can view admin dashboard
        """
        return self.is_admin(user_email)

    # --- Everyone can do these ---

    def can_ask_questions(self, user_email: str) -> bool:
        """
        Check if user can ask questions.

        Args:
            user_email: User's email address

        Returns:
            True (everyone can ask questions)
        """
        return True

    def can_accept_qa(self, user_email: str) -> bool:
        """
        Check if user can accept Q&A answers.

        Args:
            user_email: User's email address

        Returns:
            True (everyone can accept Q&A)
        """
        return True

    def can_reject_qa(self, user_email: str) -> bool:
        """
        Check if user can reject Q&A answers (escalate to admin).

        Args:
            user_email: User's email address

        Returns:
            True (everyone can reject Q&A)
        """
        return True

    def can_suggest_features(self, user_email: str) -> bool:
        """
        Check if user can suggest features.

        Args:
            user_email: User's email address

        Returns:
            True (everyone can suggest features)
        """
        return True

    def can_create_drafts(self, user_email: str) -> bool:
        """
        Check if user can create draft updates.

        Args:
            user_email: User's email address

        Returns:
            True (everyone can create drafts)
        """
        return True

    def require_admin(self, user_email: str, action: str) -> None:
        """
        Require admin permission, raise exception if not authorized.

        Args:
            user_email: User's email address
            action: Description of the action for error message

        Raises:
            PermissionError: If user is not an admin
        """
        if not self.is_admin(user_email):
            logger.warning(
                "permission_denied",
                email=user_email,
                action=action
            )
            raise PermissionError(
                f"Permission denied: Only admins can {action}. "
                f"Contact an administrator for access."
            )


# Global instance
_permission_service: Optional[PermissionService] = None


@lru_cache()
def get_permission_service() -> PermissionService:
    """
    Get or create a global permission service instance.

    Returns:
        PermissionService: The permission service
    """
    global _permission_service
    if _permission_service is None:
        _permission_service = PermissionService()
    return _permission_service

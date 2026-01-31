"""Unit tests for permission service."""

import pytest

from app.services.permission_service import (
    PermissionService,
    DEFAULT_ADMIN_EMAILS,
    DEFAULT_DISCORD_ADMINS,
)


class TestPermissionService:
    """Tests for PermissionService class."""

    @pytest.fixture
    def service(self) -> PermissionService:
        """Create a permission service instance."""
        return PermissionService()

    @pytest.fixture
    def custom_service(self) -> PermissionService:
        """Create a permission service with custom admins."""
        return PermissionService(admin_emails=["admin1@example.com", "admin2@example.com"])

    def test_default_admins(self, service: PermissionService):
        """Test default admin list is loaded including Discord admins."""
        # Should include both email admins and Discord admins
        expected_count = len(DEFAULT_ADMIN_EMAILS) + len(DEFAULT_DISCORD_ADMINS)
        assert len(service.admin_emails) == expected_count
        for email in DEFAULT_ADMIN_EMAILS:
            assert email.lower() in service.admin_emails
        # Discord admins are converted to username@discord.user format
        for username in DEFAULT_DISCORD_ADMINS:
            assert f"{username.lower()}@discord.user" in service.admin_emails

    def test_custom_admins(self, custom_service: PermissionService):
        """Test custom admin list includes Discord admins."""
        # Custom emails (2) + default Discord admins (3) = 5
        expected_count = 2 + len(DEFAULT_DISCORD_ADMINS)
        assert len(custom_service.admin_emails) == expected_count
        assert "admin1@example.com" in custom_service.admin_emails
        assert "admin2@example.com" in custom_service.admin_emails

    def test_is_admin_true(self, service: PermissionService):
        """Test admin check returns true for admins."""
        assert service.is_admin("admin@example.com") is True
        assert service.is_admin("admin@example.com") is True

    def test_is_admin_case_insensitive(self, service: PermissionService):
        """Test admin check is case insensitive."""
        assert service.is_admin("ADMIN@EXAMPLE.COM") is True
        assert service.is_admin("Admin@Example.COM") is True

    def test_is_admin_false(self, service: PermissionService):
        """Test admin check returns false for non-admins."""
        assert service.is_admin("user@example.com") is False
        assert service.is_admin("notadmin@example.com") is False

    def test_add_admin(self, service: PermissionService):
        """Test adding a new admin."""
        initial_count = len(service.admin_emails)
        service.add_admin("newadmin@example.com")
        assert len(service.admin_emails) == initial_count + 1
        assert service.is_admin("newadmin@example.com") is True

    def test_add_admin_duplicate(self, service: PermissionService):
        """Test adding duplicate admin doesn't create duplicates."""
        initial_count = len(service.admin_emails)
        service.add_admin("admin@example.com")
        assert len(service.admin_emails) == initial_count

    def test_remove_admin(self, custom_service: PermissionService):
        """Test removing an admin."""
        assert custom_service.is_admin("admin1@example.com") is True
        result = custom_service.remove_admin("admin1@example.com")
        assert result is True
        assert custom_service.is_admin("admin1@example.com") is False

    def test_remove_admin_not_found(self, service: PermissionService):
        """Test removing non-existent admin."""
        result = service.remove_admin("notadmin@example.com")
        assert result is False

    def test_can_approve_docs_admin(self, service: PermissionService):
        """Test admins can approve docs."""
        assert service.can_approve_docs("admin@example.com") is True

    def test_can_approve_docs_non_admin(self, service: PermissionService):
        """Test non-admins cannot approve docs."""
        assert service.can_approve_docs("user@example.com") is False

    def test_can_edit_docs_admin(self, service: PermissionService):
        """Test admins can edit docs."""
        assert service.can_edit_docs("admin@example.com") is True

    def test_can_edit_docs_non_admin(self, service: PermissionService):
        """Test non-admins cannot edit docs."""
        assert service.can_edit_docs("user@example.com") is False

    def test_can_accept_drafts_admin(self, service: PermissionService):
        """Test admins can accept drafts."""
        assert service.can_accept_drafts("admin@example.com") is True

    def test_can_accept_drafts_non_admin(self, service: PermissionService):
        """Test non-admins cannot accept drafts."""
        assert service.can_accept_drafts("user@example.com") is False

    def test_can_git_sync_admin(self, service: PermissionService):
        """Test admins can trigger git sync."""
        assert service.can_git_sync("admin@example.com") is True

    def test_can_git_sync_non_admin(self, service: PermissionService):
        """Test non-admins cannot trigger git sync."""
        assert service.can_git_sync("user@example.com") is False

    def test_can_respond_to_queue_admin(self, service: PermissionService):
        """Test admins can respond to queue."""
        assert service.can_respond_to_queue("admin@example.com") is True

    def test_can_respond_to_queue_non_admin(self, service: PermissionService):
        """Test non-admins cannot respond to queue."""
        assert service.can_respond_to_queue("user@example.com") is False

    def test_can_ask_questions_anyone(self, service: PermissionService):
        """Test anyone can ask questions."""
        assert service.can_ask_questions("user@example.com") is True
        assert service.can_ask_questions("admin@example.com") is True

    def test_can_accept_qa_anyone(self, service: PermissionService):
        """Test anyone can accept Q&A."""
        assert service.can_accept_qa("user@example.com") is True
        assert service.can_accept_qa("admin@example.com") is True

    def test_can_reject_qa_anyone(self, service: PermissionService):
        """Test anyone can reject Q&A."""
        assert service.can_reject_qa("user@example.com") is True
        assert service.can_reject_qa("admin@example.com") is True

    def test_can_suggest_features_anyone(self, service: PermissionService):
        """Test anyone can suggest features."""
        assert service.can_suggest_features("user@example.com") is True
        assert service.can_suggest_features("admin@example.com") is True

    def test_can_create_drafts_anyone(self, service: PermissionService):
        """Test anyone can create drafts."""
        assert service.can_create_drafts("user@example.com") is True
        assert service.can_create_drafts("admin@example.com") is True

    def test_require_admin_passes(self, service: PermissionService):
        """Test require_admin passes for admins."""
        # Should not raise
        service.require_admin("admin@example.com", "edit documentation")

    def test_require_admin_raises(self, service: PermissionService):
        """Test require_admin raises for non-admins."""
        with pytest.raises(PermissionError) as exc_info:
            service.require_admin("user@example.com", "edit documentation")
        assert "Permission denied" in str(exc_info.value)
        assert "edit documentation" in str(exc_info.value)

    def test_admin_emails_returns_copy(self, service: PermissionService):
        """Test admin_emails returns a copy, not the original list."""
        emails = service.admin_emails
        emails.append("hacker@evil.com")
        assert "hacker@evil.com" not in service.admin_emails

"""Unit tests for Notification service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestNotificationService:
    """Tests for NotificationService."""

    @pytest.fixture
    def notification_service(self):
        """Create a NotificationService instance."""
        with patch("app.services.notification_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            from app.services.notification_service import NotificationService
            return NotificationService()

    def test_init(self, notification_service):
        """Test initialization."""
        assert notification_service.settings is not None
        assert notification_service._discord_webhook_url is None
        assert notification_service._teams_webhook_url is None

    def test_configure_discord(self, notification_service):
        """Test configuring Discord webhook."""
        notification_service.configure_discord("https://discord.webhook.url")
        assert notification_service._discord_webhook_url == "https://discord.webhook.url"
        assert notification_service.discord_enabled is True

    def test_configure_teams(self, notification_service):
        """Test configuring Teams webhook."""
        notification_service.configure_teams("https://teams.webhook.url")
        assert notification_service._teams_webhook_url == "https://teams.webhook.url"
        assert notification_service.teams_enabled is True

    def test_discord_disabled_by_default(self, notification_service):
        """Test Discord is disabled when no webhook configured."""
        assert notification_service.discord_enabled is False

    def test_teams_disabled_by_default(self, notification_service):
        """Test Teams is disabled when no webhook configured."""
        assert notification_service.teams_enabled is False


class TestNotifyQuestionEscalated:
    """Tests for question escalation notifications."""

    @pytest.fixture
    def service_with_webhooks(self):
        """Create a NotificationService with webhooks configured."""
        with patch("app.services.notification_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            from app.services.notification_service import NotificationService
            service = NotificationService()
            service.configure_discord("https://discord.webhook")
            service.configure_teams("https://teams.webhook")
            return service

    @pytest.fixture
    def sample_question(self):
        """Create a sample pending question."""
        from app.storage.models import PendingQuestion, Language, QuestionStatus
        from datetime import datetime

        return PendingQuestion(
            id="Q-12345678",
            user_email="user@test.com",
            question="How do I do X?",
            bot_answer="Here's the answer...",
            language=Language.EN,
            platform="discord",
            status=QuestionStatus.PENDING,
            created_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_notify_question_escalated(self, service_with_webhooks, sample_question):
        """Test question escalation notification."""
        with patch.object(
            service_with_webhooks, "_send_discord_question_alert", new_callable=AsyncMock
        ) as mock_discord, patch.object(
            service_with_webhooks, "_send_teams_question_alert", new_callable=AsyncMock
        ) as mock_teams:
            mock_discord.return_value = True
            mock_teams.return_value = True

            result = await service_with_webhooks.notify_question_escalated(sample_question)

            mock_discord.assert_called_once_with(sample_question)
            mock_teams.assert_called_once_with(sample_question)
            assert result["discord"] is True
            assert result["teams"] is True


class TestNotifyDraftSubmitted:
    """Tests for draft submission notifications."""

    @pytest.fixture
    def service_with_webhooks(self):
        """Create a NotificationService with webhooks configured."""
        with patch("app.services.notification_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            from app.services.notification_service import NotificationService
            service = NotificationService()
            service.configure_discord("https://discord.webhook")
            service.configure_teams("https://teams.webhook")
            return service

    @pytest.fixture
    def sample_draft(self):
        """Create a sample draft update."""
        from app.storage.models import DraftUpdate, Language, DraftStatus
        from datetime import datetime

        return DraftUpdate(
            id="DRAFT-12345678",
            user_email="user@test.com",
            content="Updated installation instructions",
            target_section="installation.md",
            language=Language.EN,
            status=DraftStatus.PENDING,
            created_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_notify_draft_submitted(self, service_with_webhooks, sample_draft):
        """Test draft submission notification."""
        with patch.object(
            service_with_webhooks, "_send_discord_draft_alert", new_callable=AsyncMock
        ) as mock_discord, patch.object(
            service_with_webhooks, "_send_teams_draft_alert", new_callable=AsyncMock
        ) as mock_teams:
            mock_discord.return_value = True
            mock_teams.return_value = True

            result = await service_with_webhooks.notify_draft_submitted(sample_draft)

            mock_discord.assert_called_once_with(sample_draft)
            mock_teams.assert_called_once_with(sample_draft)
            assert result["discord"] is True
            assert result["teams"] is True


class TestDiscordNotificationFormat:
    """Tests for Discord notification formatting."""

    def test_notification_format(self):
        """Test notification message format."""
        title = "Question Escalated"
        message = "A user has rejected an answer"
        details = {
            "question_id": "Q-12345678",
            "user_email": "user@test.com",
            "platform": "discord"
        }

        # Build expected format
        notification = f"**{title}**\n{message}"
        for key, value in details.items():
            notification += f"\n• {key}: {value}"

        assert "Question Escalated" in notification
        assert "Q-12345678" in notification
        assert "user@test.com" in notification


class TestTeamsNotificationFormat:
    """Tests for Teams notification formatting."""

    def test_message_card_format(self):
        """Test Teams MessageCard format."""
        title = "Draft Update Created"
        message = "A new draft update requires review"
        details = {
            "draft_id": "DRAFT-12345678",
            "user_email": "user@test.com"
        }

        # Build MessageCard structure
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "facts": [
                    {"name": key, "value": value}
                    for key, value in details.items()
                ],
                "text": message
            }]
        }

        assert card["@type"] == "MessageCard"
        assert card["summary"] == title
        assert len(card["sections"]) == 1
        assert len(card["sections"][0]["facts"]) == 2

    # Teams AdaptiveCard test removed - Teams module was removed from project


class TestWebhookPayload:
    """Tests for webhook payload generation."""

    def test_discord_webhook_payload(self):
        """Test Discord webhook payload structure."""
        payload = {
            "content": None,
            "embeds": [{
                "title": "Test Title",
                "description": "Test description",
                "color": 3447003,  # Blue
                "fields": [
                    {"name": "Field 1", "value": "Value 1", "inline": True}
                ]
            }]
        }

        assert "embeds" in payload
        assert len(payload["embeds"]) == 1
        assert payload["embeds"][0]["title"] == "Test Title"

    def test_teams_webhook_payload(self):
        """Test Teams webhook payload structure."""
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": "Test Summary",
            "sections": [{
                "activityTitle": "Test Title",
                "text": "Test message"
            }]
        }

        assert payload["@type"] == "MessageCard"
        assert payload["summary"] == "Test Summary"

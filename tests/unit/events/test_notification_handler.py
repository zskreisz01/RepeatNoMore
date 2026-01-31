"""Unit tests for NotificationHandler - Discord notifications for drafts and questions."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.events.types import DocumentEvent, EventData
from app.events.handlers.notification_handler import NotificationHandler


@pytest.fixture
def mock_discord_channel():
    """Create a mock Discord channel."""
    channel = MagicMock()
    channel.name = "draft-admin-process"
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def mock_questions_channel():
    """Create a mock Discord channel for questions."""
    channel = MagicMock()
    channel.name = "questions-admin-process"
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def mock_discord_guild(mock_discord_channel, mock_questions_channel):
    """Create a mock Discord guild."""
    guild = MagicMock()
    guild.name = "Test Guild"
    guild.text_channels = [mock_discord_channel, mock_questions_channel]
    guild.default_role = MagicMock()
    guild.me = MagicMock()
    guild.roles = []
    guild.create_text_channel = AsyncMock(return_value=mock_discord_channel)
    return guild


@pytest.fixture
def mock_discord_bot(mock_discord_guild):
    """Create a mock Discord bot."""
    bot = MagicMock()
    bot.guilds = [mock_discord_guild]
    return bot


@pytest.fixture
def notification_handler(mock_discord_bot):
    """Create NotificationHandler with mock bot."""
    handler = NotificationHandler(bot=mock_discord_bot)
    return handler


class TestNotificationHandlerInitialization:
    """Tests for NotificationHandler initialization."""

    def test_init_sets_channel_names(self):
        """Test that initialization sets correct channel names."""
        handler = NotificationHandler()

        assert handler._draft_admin_channel_name == "draft-admin-process"
        assert handler._questions_admin_channel_name == "questions-admin-process"

    def test_init_without_bot(self):
        """Test initialization without bot."""
        handler = NotificationHandler(bot=None)

        assert handler._bot is None

    def test_set_bot(self, mock_discord_bot):
        """Test setting bot after initialization."""
        handler = NotificationHandler()
        handler.set_bot(mock_discord_bot)

        assert handler._bot is mock_discord_bot


class TestDraftNotifications:
    """Tests for draft-related notifications to draft-admin-process channel."""

    @pytest.mark.asyncio
    async def test_draft_created_sends_to_draft_channel(
        self, notification_handler, mock_discord_channel
    ):
        """Test that DRAFT_CREATED sends notification to draft-admin-process channel."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_CREATED,
            draft_id="DRAFT-001",
            draft_content="This is the draft content for the new documentation section.",
            target_section="getting-started.md",
            user_email="user@test.com",
        )

        await notification_handler.handle_event(event)

        # Verify channel.send was called with an embed
        mock_discord_channel.send.assert_called_once()
        call_kwargs = mock_discord_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        assert embed.title == "New Draft Submitted"
        assert "DRAFT-001" in str(embed.fields)

    @pytest.mark.asyncio
    async def test_draft_created_includes_content_preview(
        self, notification_handler, mock_discord_channel
    ):
        """Test that draft notification includes content preview."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_CREATED,
            draft_id="DRAFT-002",
            draft_content="Short preview content",
            target_section="architecture.md",
            user_email="user@test.com",
        )

        await notification_handler.handle_event(event)

        call_kwargs = mock_discord_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        # Check that content preview field exists
        field_names = [f.name for f in embed.fields]
        assert "Content Preview" in field_names

    @pytest.mark.asyncio
    async def test_draft_created_truncates_long_content(
        self, notification_handler, mock_discord_channel
    ):
        """Test that long draft content is truncated in preview."""
        long_content = "A" * 1000  # Content longer than 500 chars
        event = EventData(
            event_type=DocumentEvent.DRAFT_CREATED,
            draft_id="DRAFT-003",
            draft_content=long_content,
            target_section="docs.md",
            user_email="user@test.com",
        )

        await notification_handler.handle_event(event)

        call_kwargs = mock_discord_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        # Find the content preview field and check truncation
        for field in embed.fields:
            if field.name == "Content Preview":
                assert "..." in field.value

    @pytest.mark.asyncio
    async def test_draft_approved_sends_to_draft_channel(
        self, notification_handler, mock_discord_channel
    ):
        """Test that DRAFT_APPROVED sends notification to draft-admin-process channel."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_APPROVED,
            draft_id="DRAFT-004",
            target_section="updated-section.md",
            user_email="admin@test.com",
        )

        await notification_handler.handle_event(event)

        mock_discord_channel.send.assert_called_once()
        call_kwargs = mock_discord_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        assert embed.title == "Draft Approved"
        assert "DRAFT-004" in embed.description

    @pytest.mark.asyncio
    async def test_draft_rejected_sends_to_draft_channel(
        self, notification_handler, mock_discord_channel
    ):
        """Test that DRAFT_REJECTED sends notification to draft-admin-process channel."""
        event = EventData(
            event_type=DocumentEvent.DRAFT_REJECTED,
            draft_id="DRAFT-005",
            user_email="admin@test.com",
            metadata={"reason": "Content does not meet quality standards"},
        )

        await notification_handler.handle_event(event)

        mock_discord_channel.send.assert_called_once()
        call_kwargs = mock_discord_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        assert embed.title == "Draft Rejected"
        assert "DRAFT-005" in embed.description

        # Check reason is included
        field_values = [f.value for f in embed.fields]
        assert any("quality standards" in v for v in field_values)


class TestQuestionEscalationNotifications:
    """Tests for escalated question notifications to questions-admin-process channel."""

    @pytest.mark.asyncio
    async def test_question_created_sends_to_questions_channel(
        self, notification_handler, mock_questions_channel
    ):
        """Test that QUESTION_CREATED sends notification to questions-admin-process channel."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_CREATED,
            question_id="Q-001",
            question_text="How do I configure the database connection?",
            user_email="user@test.com",
            metadata={
                "platform": "discord",
                "rejection_reason": "The bot's answer was incorrect",
            },
        )

        await notification_handler.handle_event(event)

        # Verify questions channel received the notification
        mock_questions_channel.send.assert_called_once()
        call_kwargs = mock_questions_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        assert embed.title == "Question Escalated for Review"
        assert "Q-001" in str(embed.fields)

    @pytest.mark.asyncio
    async def test_question_escalation_includes_question_text(
        self, notification_handler, mock_questions_channel
    ):
        """Test that escalation notification includes the question text."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_CREATED,
            question_id="Q-002",
            question_text="What is the default configuration for the API?",
            user_email="user@test.com",
            metadata={"platform": "api"},
        )

        await notification_handler.handle_event(event)

        call_kwargs = mock_questions_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        # Check that question text is included
        field_values = [f.value for f in embed.fields]
        assert any("default configuration" in v for v in field_values)

    @pytest.mark.asyncio
    async def test_question_escalation_includes_rejection_reason(
        self, notification_handler, mock_questions_channel
    ):
        """Test that escalation notification includes rejection reason."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_CREATED,
            question_id="Q-003",
            question_text="How do I deploy to production?",
            user_email="user@test.com",
            metadata={
                "platform": "discord",
                "rejection_reason": "The answer was outdated",
            },
        )

        await notification_handler.handle_event(event)

        call_kwargs = mock_questions_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        # Check that rejection reason is included
        field_names = [f.name for f in embed.fields]
        field_values = [f.value for f in embed.fields]

        assert "Rejection Reason" in field_names
        assert any("outdated" in v for v in field_values)

    @pytest.mark.asyncio
    async def test_question_escalation_includes_platform(
        self, notification_handler, mock_questions_channel
    ):
        """Test that escalation notification includes platform info."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_CREATED,
            question_id="Q-004",
            question_text="Test question",
            user_email="user@test.com",
            metadata={"platform": "teams"},
        )

        await notification_handler.handle_event(event)

        call_kwargs = mock_questions_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        # Check that platform is included
        field_values = [f.value for f in embed.fields]
        assert any("Teams" in v for v in field_values)

    @pytest.mark.asyncio
    async def test_question_escalation_shows_action_hint(
        self, notification_handler, mock_questions_channel
    ):
        """Test that escalation notification shows action hint in footer."""
        event = EventData(
            event_type=DocumentEvent.QUESTION_CREATED,
            question_id="Q-005",
            question_text="Test question",
            user_email="user@test.com",
            metadata={"platform": "discord"},
        )

        await notification_handler.handle_event(event)

        call_kwargs = mock_questions_channel.send.call_args[1]
        embed = call_kwargs["embed"]

        # Check footer has action hint
        assert "/answer-question" in embed.footer.text
        assert "Q-005" in embed.footer.text


class TestChannelCreation:
    """Tests for channel creation when channels don't exist."""

    @pytest.mark.asyncio
    async def test_creates_draft_channel_if_not_exists(self, mock_discord_bot, mock_discord_guild):
        """Test that draft channel is created if it doesn't exist."""
        # Set up guild with no channels
        mock_discord_guild.text_channels = []
        new_channel = MagicMock()
        new_channel.name = "draft-admin-process"
        new_channel.send = AsyncMock()
        mock_discord_guild.create_text_channel = AsyncMock(return_value=new_channel)

        handler = NotificationHandler(bot=mock_discord_bot)

        event = EventData(
            event_type=DocumentEvent.DRAFT_CREATED,
            draft_id="DRAFT-001",
            user_email="user@test.com",
        )

        await handler.handle_event(event)

        # Verify channel was created
        mock_discord_guild.create_text_channel.assert_called()
        call_args = mock_discord_guild.create_text_channel.call_args
        assert call_args[1]["name"] == "draft-admin-process"

    @pytest.mark.asyncio
    async def test_creates_questions_channel_if_not_exists(
        self, mock_discord_bot, mock_discord_guild
    ):
        """Test that questions channel is created if it doesn't exist."""
        # Set up guild with only draft channel
        draft_channel = MagicMock()
        draft_channel.name = "draft-admin-process"
        mock_discord_guild.text_channels = [draft_channel]

        new_channel = MagicMock()
        new_channel.name = "questions-admin-process"
        new_channel.send = AsyncMock()
        mock_discord_guild.create_text_channel = AsyncMock(return_value=new_channel)

        handler = NotificationHandler(bot=mock_discord_bot)

        event = EventData(
            event_type=DocumentEvent.QUESTION_CREATED,
            question_id="Q-001",
            question_text="Test question",
            user_email="user@test.com",
            metadata={"platform": "discord"},
        )

        await handler.handle_event(event)

        # Verify questions channel was created
        mock_discord_guild.create_text_channel.assert_called()
        call_args = mock_discord_guild.create_text_channel.call_args
        assert call_args[1]["name"] == "questions-admin-process"


class TestNoBot:
    """Tests for handling when no bot is available."""

    @pytest.mark.asyncio
    async def test_handles_no_bot_gracefully(self):
        """Test that handler handles missing bot gracefully."""
        handler = NotificationHandler(bot=None)

        event = EventData(
            event_type=DocumentEvent.DRAFT_CREATED,
            draft_id="DRAFT-001",
            user_email="user@test.com",
        )

        # Should not raise exception
        await handler.handle_event(event)


class TestQuestionAnsweredNotification:
    """Tests for QUESTION_ANSWERED notification (DM to user)."""

    @pytest.mark.asyncio
    async def test_question_answered_sends_dm(self, mock_discord_bot, mock_discord_guild):
        """Test that QUESTION_ANSWERED sends DM to user."""
        # Set up mock member
        mock_member = MagicMock()
        mock_member.name = "testuser"
        mock_member.send = AsyncMock()
        mock_discord_guild.members = [mock_member]

        handler = NotificationHandler(bot=mock_discord_bot)

        event = EventData(
            event_type=DocumentEvent.QUESTION_ANSWERED,
            question_id="Q-001",
            question_text="How do I configure the database?",
            answer_text="You can configure the database by editing the config.py file.",
            user_email="testuser@discord.user",
        )

        await handler.handle_event(event)

        # Verify DM was sent
        mock_member.send.assert_called_once()
        call_kwargs = mock_member.send.call_args[1]
        embed = call_kwargs["embed"]

        assert embed.title == "Your Question Has Been Answered!"

    @pytest.mark.asyncio
    async def test_question_answered_handles_user_not_found(
        self, mock_discord_bot, mock_discord_guild
    ):
        """Test handling when user is not found for DM."""
        mock_discord_guild.members = []  # No members

        handler = NotificationHandler(bot=mock_discord_bot)

        event = EventData(
            event_type=DocumentEvent.QUESTION_ANSWERED,
            question_id="Q-002",
            question_text="Test question",
            answer_text="Test answer",
            user_email="nonexistent@discord.user",
        )

        # Should not raise exception
        await handler.handle_event(event)

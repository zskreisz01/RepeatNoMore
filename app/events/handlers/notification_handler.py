"""Notification handler for document events."""

from typing import Optional

import discord

from app.events.types import DocumentEvent, EventData
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NotificationHandler:
    """
    Handler for sending Discord notifications when document events occur.

    Posts to the draft-admin-process channel for drafts,
    questions-admin-process channel for escalated questions,
    and sends DMs to users for question answers.
    """

    def __init__(self, bot: Optional[discord.Client] = None):
        """
        Initialize the notification handler.

        Args:
            bot: Discord bot client for sending messages
        """
        self._bot = bot
        self._draft_admin_channel_name = "draft-admin-process"
        self._questions_admin_channel_name = "questions-admin-process"
        logger.info("notification_handler_initialized")

    def set_bot(self, bot: discord.Client) -> None:
        """
        Set the Discord bot client.

        Args:
            bot: Discord bot client
        """
        self._bot = bot
        logger.debug("notification_handler_bot_set")

    async def handle_event(self, event: EventData) -> None:
        """
        Handle events that require notifications.

        Args:
            event: The event data
        """
        if not self._bot:
            logger.warning("notification_handler_no_bot")
            return

        # Route to appropriate notification method
        handlers = {
            DocumentEvent.DRAFT_CREATED: self._notify_draft_created,
            DocumentEvent.DRAFT_APPROVED: self._notify_draft_approved,
            DocumentEvent.DRAFT_REJECTED: self._notify_draft_rejected,
            DocumentEvent.QUESTION_CREATED: self._notify_question_escalated,
            DocumentEvent.QUESTION_ANSWERED: self._notify_question_answered,
        }

        handler = handlers.get(event.event_type)
        if handler:
            await handler(event)

    async def _notify_draft_created(self, event: EventData) -> None:
        """
        Notify admins about a new draft in the draft-admin-process channel.

        Args:
            event: The event data containing draft information
        """
        channel = await self._get_or_create_channel(
            self._draft_admin_channel_name,
            topic="Draft updates and admin notifications from RepeatNoMore",
        )
        if not channel:
            logger.warning("could_not_get_draft_admin_channel")
            return

        embed = discord.Embed(
            title="New Draft Submitted",
            description="A new draft update has been submitted for review.",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Draft ID",
            value=event.draft_id or "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Target Section",
            value=event.target_section or "Not specified",
            inline=True,
        )
        embed.add_field(
            name="Submitted By",
            value=event.user_email or "Unknown",
            inline=True,
        )

        if event.draft_content:
            preview = event.draft_content[:500]
            if len(event.draft_content) > 500:
                preview += "..."
            embed.add_field(
                name="Content Preview",
                value=f"```\n{preview}\n```",
                inline=False,
            )

        # Add action buttons hint
        embed.set_footer(
            text=f"Use /accept-draft {event.draft_id} or /reject-draft {event.draft_id} <reason>"
        )

        await channel.send(embed=embed)
        logger.info(
            "draft_notification_sent",
            draft_id=event.draft_id,
            channel=channel.name,
        )

    async def _notify_draft_approved(self, event: EventData) -> None:
        """Notify that a draft has been approved."""
        channel = await self._get_or_create_channel(
            self._draft_admin_channel_name,
            topic="Draft updates and admin notifications from RepeatNoMore",
        )
        if not channel:
            return

        embed = discord.Embed(
            title="Draft Approved",
            description=f"Draft **{event.draft_id}** has been approved and applied.",
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Approved By",
            value=event.user_email or "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Target",
            value=event.target_section or "Not specified",
            inline=True,
        )

        await channel.send(embed=embed)

    async def _notify_draft_rejected(self, event: EventData) -> None:
        """Notify that a draft has been rejected."""
        channel = await self._get_or_create_channel(
            self._draft_admin_channel_name,
            topic="Draft updates and admin notifications from RepeatNoMore",
        )
        if not channel:
            return

        embed = discord.Embed(
            title="Draft Rejected",
            description=f"Draft **{event.draft_id}** has been rejected.",
            color=discord.Color.red(),
        )
        embed.add_field(
            name="Rejected By",
            value=event.user_email or "Unknown",
            inline=True,
        )
        reason = event.metadata.get("reason", "No reason provided")
        embed.add_field(
            name="Reason",
            value=reason,
            inline=False,
        )

        await channel.send(embed=embed)

    async def _notify_question_escalated(self, event: EventData) -> None:
        """
        Notify admins about an escalated question in the questions-admin-process channel.

        Args:
            event: The event data containing question information
        """
        channel = await self._get_or_create_channel(
            self._questions_admin_channel_name,
            topic="Escalated questions requiring admin review from RepeatNoMore",
        )
        if not channel:
            logger.warning("could_not_get_questions_admin_channel")
            return

        embed = discord.Embed(
            title="Question Escalated for Review",
            description="A user has rejected the bot's answer and escalated the question for admin review.",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Question ID",
            value=event.question_id or "Unknown",
            inline=True,
        )
        embed.add_field(
            name="Submitted By",
            value=event.user_email or "Unknown",
            inline=True,
        )

        platform = event.metadata.get("platform", "unknown")
        embed.add_field(
            name="Platform",
            value=platform.capitalize(),
            inline=True,
        )

        if event.question_text:
            question_preview = event.question_text[:500]
            if len(event.question_text) > 500:
                question_preview += "..."
            embed.add_field(
                name="Question",
                value=question_preview,
                inline=False,
            )

        rejection_reason = event.metadata.get("rejection_reason")
        if rejection_reason:
            embed.add_field(
                name="Rejection Reason",
                value=rejection_reason[:500],
                inline=False,
            )

        # Add action hint
        embed.set_footer(
            text=f"Use /answer-question {event.question_id} <your_answer> to respond"
        )

        await channel.send(embed=embed)
        logger.info(
            "question_escalation_notification_sent",
            question_id=event.question_id,
            channel=channel.name,
        )

    async def _notify_question_answered(self, event: EventData) -> None:
        """
        Notify the user who asked the question via DM.

        Args:
            event: The event data containing question and answer info
        """
        if not event.user_email:
            logger.warning("no_user_email_for_notification")
            return

        # Try to find the user by their Discord identifier
        # The user_email format is "username@discord.user"
        username = event.user_email.replace("@discord.user", "")

        user = None
        for guild in self._bot.guilds:
            for member in guild.members:
                if member.name == username:
                    user = member
                    break
            if user:
                break

        if not user:
            logger.warning(
                "user_not_found_for_notification",
                username=username,
            )
            return

        try:
            embed = discord.Embed(
                title="Your Question Has Been Answered!",
                description="An administrator has answered your escalated question.",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="Question ID",
                value=event.question_id or "Unknown",
                inline=True,
            )
            if event.question_text:
                embed.add_field(
                    name="Your Question",
                    value=event.question_text[:500],
                    inline=False,
                )
            if event.answer_text:
                embed.add_field(
                    name="Answer",
                    value=event.answer_text[:1000],
                    inline=False,
                )

            await user.send(embed=embed)
            logger.info(
                "question_answer_notification_sent",
                question_id=event.question_id,
                user=username,
            )

        except discord.Forbidden:
            logger.warning(
                "cannot_dm_user",
                username=username,
                reason="DMs disabled or blocked",
            )
        except Exception as e:
            logger.error(
                "notification_dm_failed",
                username=username,
                error=str(e),
            )

    async def _get_or_create_channel(
        self,
        channel_name: str,
        topic: str,
    ) -> Optional[discord.TextChannel]:
        """
        Get or create a channel for notifications.

        Args:
            channel_name: Name of the channel to get or create
            topic: Topic description for the channel

        Returns:
            The channel, or None if it couldn't be found/created
        """
        if not self._bot or not self._bot.guilds:
            return None

        # Use the first guild (assuming single-server deployment)
        guild = self._bot.guilds[0]

        # Look for existing channel
        for channel in guild.text_channels:
            if channel.name == channel_name:
                return channel

        # Try to create the channel
        try:
            # Create with restricted permissions (admins only by default)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                ),
                guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                ),
            }

            # Add admin role permissions if it exists
            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                    )

            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=topic,
            )

            logger.info(
                "admin_channel_created",
                channel_name=channel_name,
                guild=guild.name,
            )

            return channel

        except discord.Forbidden:
            logger.error(
                "cannot_create_admin_channel",
                channel_name=channel_name,
                reason="Missing permissions",
            )
            return None
        except Exception as e:
            logger.error(
                "admin_channel_creation_failed",
                channel_name=channel_name,
                error=str(e),
            )
            return None

"""Notification service for admin alerts via Discord and Teams."""

from functools import lru_cache
from typing import Optional
import json

import httpx

from app.config import get_settings
from app.storage.models import PendingQuestion, DraftUpdate
from app.utils.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """Service for sending notifications to admins via Discord and Teams."""

    def __init__(self):
        """Initialize notification service."""
        self.settings = get_settings()
        self._discord_webhook_url: Optional[str] = None
        self._teams_webhook_url: Optional[str] = None
        logger.info("notification_service_initialized")

    def configure_discord(self, webhook_url: str) -> None:
        """
        Configure Discord webhook URL.

        Args:
            webhook_url: Discord webhook URL
        """
        self._discord_webhook_url = webhook_url
        logger.info("discord_webhook_configured")

    def configure_teams(self, webhook_url: str) -> None:
        """
        Configure Teams webhook URL.

        Args:
            webhook_url: Teams incoming webhook URL
        """
        self._teams_webhook_url = webhook_url
        logger.info("teams_webhook_configured")

    @property
    def discord_enabled(self) -> bool:
        """Check if Discord notifications are enabled."""
        return bool(self._discord_webhook_url)

    @property
    def teams_enabled(self) -> bool:
        """Check if Teams notifications are enabled."""
        return bool(self._teams_webhook_url)

    async def notify_question_escalated(self, question: PendingQuestion) -> dict:
        """
        Notify admins about an escalated question.

        Args:
            question: The escalated question

        Returns:
            Dictionary with notification results
        """
        results = {"discord": False, "teams": False}

        if self.discord_enabled:
            results["discord"] = await self._send_discord_question_alert(question)

        if self.teams_enabled:
            results["teams"] = await self._send_teams_question_alert(question)

        logger.info(
            "question_escalation_notified",
            question_id=question.id,
            discord=results["discord"],
            teams=results["teams"]
        )

        return results

    async def notify_draft_submitted(self, draft: DraftUpdate) -> dict:
        """
        Notify admins about a new draft update.

        Args:
            draft: The submitted draft

        Returns:
            Dictionary with notification results
        """
        results = {"discord": False, "teams": False}

        if self.discord_enabled:
            results["discord"] = await self._send_discord_draft_alert(draft)

        if self.teams_enabled:
            results["teams"] = await self._send_teams_draft_alert(draft)

        logger.info(
            "draft_submission_notified",
            draft_id=draft.id,
            discord=results["discord"],
            teams=results["teams"]
        )

        return results

    async def _send_discord_question_alert(self, question: PendingQuestion) -> bool:
        """Send question alert to Discord."""
        if not self._discord_webhook_url:
            return False

        embed = {
            "title": "Question Escalated",
            "description": question.question[:1000],
            "color": 15158332,  # Red
            "fields": [
                {
                    "name": "Question ID",
                    "value": question.id,
                    "inline": True
                },
                {
                    "name": "User",
                    "value": question.user_email or "Unknown",
                    "inline": True
                },
                {
                    "name": "Platform",
                    "value": question.platform.capitalize(),
                    "inline": True
                },
                {
                    "name": "Bot Answer",
                    "value": question.bot_answer[:500] + ("..." if len(question.bot_answer) > 500 else ""),
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Rejection Reason: {question.rejection_reason or 'Not specified'}"
            }
        }

        if question.rejection_reason:
            embed["fields"].append({
                "name": "Rejection Reason",
                "value": question.rejection_reason[:500],
                "inline": False
            })

        payload = {
            "embeds": [embed],
            "content": "A question has been escalated and needs admin attention."
        }

        return await self._send_discord_webhook(payload)

    async def _send_discord_draft_alert(self, draft: DraftUpdate) -> bool:
        """Send draft alert to Discord."""
        if not self._discord_webhook_url:
            return False

        embed = {
            "title": "New Draft Update Submitted",
            "description": draft.description or draft.content[:500],
            "color": 3447003,  # Blue
            "fields": [
                {
                    "name": "Draft ID",
                    "value": draft.id,
                    "inline": True
                },
                {
                    "name": "User",
                    "value": draft.user_email or "Unknown",
                    "inline": True
                },
                {
                    "name": "Target Section",
                    "value": draft.target_section or "Not specified",
                    "inline": True
                },
                {
                    "name": "Language",
                    "value": draft.language.upper(),
                    "inline": True
                }
            ]
        }

        payload = {
            "embeds": [embed],
            "content": "A new draft update has been submitted for review."
        }

        return await self._send_discord_webhook(payload)

    async def _send_discord_webhook(self, payload: dict) -> bool:
        """
        Send payload to Discord webhook.

        Args:
            payload: Discord webhook payload

        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._discord_webhook_url,
                    json=payload,
                    timeout=10.0
                )
                if response.status_code in (200, 204):
                    return True
                logger.warning(
                    "discord_webhook_failed",
                    status=response.status_code,
                    body=response.text[:200]
                )
                return False
        except Exception as e:
            logger.error("discord_webhook_error", error=str(e))
            return False

    async def _send_teams_question_alert(self, question: PendingQuestion) -> bool:
        """Send question alert to Teams."""
        if not self._teams_webhook_url:
            return False

        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "FF0000",
            "summary": "Question Escalated",
            "sections": [{
                "activityTitle": "Question Escalated",
                "activitySubtitle": f"From: {question.user_email or 'Unknown'} via {question.platform.capitalize()}",
                "facts": [
                    {"name": "Question ID", "value": question.id},
                    {"name": "Question", "value": question.question[:500]},
                    {"name": "Bot Answer", "value": question.bot_answer[:500]},
                ],
                "markdown": True
            }]
        }

        if question.rejection_reason:
            card["sections"][0]["facts"].append({
                "name": "Rejection Reason",
                "value": question.rejection_reason
            })

        return await self._send_teams_webhook(card)

    async def _send_teams_draft_alert(self, draft: DraftUpdate) -> bool:
        """Send draft alert to Teams."""
        if not self._teams_webhook_url:
            return False

        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0078D7",
            "summary": "New Draft Update",
            "sections": [{
                "activityTitle": "New Draft Update Submitted",
                "activitySubtitle": f"From: {draft.user_email or 'Unknown'}",
                "facts": [
                    {"name": "Draft ID", "value": draft.id},
                    {"name": "Target Section", "value": draft.target_section or "Not specified"},
                    {"name": "Description", "value": draft.description or draft.content[:500]},
                    {"name": "Language", "value": draft.language.upper()},
                ],
                "markdown": True
            }]
        }

        return await self._send_teams_webhook(card)

    async def _send_teams_webhook(self, card: dict) -> bool:
        """
        Send payload to Teams webhook.

        Args:
            card: Teams message card payload

        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._teams_webhook_url,
                    json=card,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return True
                logger.warning(
                    "teams_webhook_failed",
                    status=response.status_code,
                    body=response.text[:200]
                )
                return False
        except Exception as e:
            logger.error("teams_webhook_error", error=str(e))
            return False

    async def send_custom_notification(
        self,
        title: str,
        message: str,
        color: str = "blue"
    ) -> dict:
        """
        Send a custom notification to all configured channels.

        Args:
            title: Notification title
            message: Notification message
            color: Color (blue, red, green, yellow)

        Returns:
            Dictionary with notification results
        """
        colors = {
            "blue": (3447003, "0078D7"),
            "red": (15158332, "FF0000"),
            "green": (3066993, "00FF00"),
            "yellow": (16776960, "FFFF00")
        }
        discord_color, teams_color = colors.get(color, colors["blue"])

        results = {"discord": False, "teams": False}

        if self.discord_enabled:
            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": discord_color
                }]
            }
            results["discord"] = await self._send_discord_webhook(payload)

        if self.teams_enabled:
            card = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": teams_color,
                "summary": title,
                "sections": [{
                    "activityTitle": title,
                    "text": message,
                    "markdown": True
                }]
            }
            results["teams"] = await self._send_teams_webhook(card)

        return results


# Global instance
_notification_service: Optional[NotificationService] = None


@lru_cache()
def get_notification_service() -> NotificationService:
    """
    Get or create a global notification service instance.

    Returns:
        NotificationService: The notification service
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service

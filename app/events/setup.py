"""Event system setup and initialization."""

from typing import Optional

import discord

from app.events import DocumentEvent, get_event_dispatcher
from app.events.handlers import (
    MkDocsHandler,
    GitHandler,
    NotificationHandler,
    IndexHandler,
    get_index_handler,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Global handler instances
_mkdocs_handler: Optional[MkDocsHandler] = None
_git_handler: Optional[GitHandler] = None
_notification_handler: Optional[NotificationHandler] = None
_index_handler: Optional[IndexHandler] = None


def setup_event_handlers(bot: Optional[discord.Client] = None) -> None:
    """
    Initialize and register all event handlers.

    Args:
        bot: Optional Discord bot client for notification handler
    """
    global _mkdocs_handler, _git_handler, _notification_handler, _index_handler

    dispatcher = get_event_dispatcher()

    # Initialize handlers
    _mkdocs_handler = MkDocsHandler()
    _git_handler = GitHandler()
    _notification_handler = NotificationHandler(bot)
    _index_handler = get_index_handler()

    # Register MkDocs handler for document events
    dispatcher.subscribe(DocumentEvent.DOC_CREATED, _mkdocs_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DOC_UPDATED, _mkdocs_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DOC_DELETED, _mkdocs_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DRAFT_APPROVED, _mkdocs_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.QUESTION_ANSWERED, _mkdocs_handler.handle_event)

    # Register Git handler for sync events
    dispatcher.subscribe(DocumentEvent.DRAFT_APPROVED, _git_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.QUESTION_ANSWERED, _git_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DOC_UPDATED, _git_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.GIT_SYNC_REQUESTED, _git_handler.handle_event)

    # Register Notification handler for draft/question events
    dispatcher.subscribe(DocumentEvent.DRAFT_CREATED, _notification_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DRAFT_APPROVED, _notification_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DRAFT_REJECTED, _notification_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.QUESTION_CREATED, _notification_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.QUESTION_ANSWERED, _notification_handler.handle_event)

    # Register Index handler for automatic vector store updates
    dispatcher.subscribe(DocumentEvent.DOC_CREATED, _index_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DOC_UPDATED, _index_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DOC_DELETED, _index_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DRAFT_CREATED, _index_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.DRAFT_APPROVED, _index_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.QUESTION_CREATED, _index_handler.handle_event)
    dispatcher.subscribe(DocumentEvent.QUESTION_ANSWERED, _index_handler.handle_event)

    logger.info(
        "event_handlers_registered",
        handler_count=4,
        events=["mkdocs", "git", "notification", "index"]
    )


def set_notification_bot(bot: discord.Client) -> None:
    """
    Set the Discord bot for the notification handler.

    Call this after the bot is ready to enable Discord notifications.

    Args:
        bot: Discord bot client
    """
    global _notification_handler

    if _notification_handler:
        _notification_handler.set_bot(bot)
        logger.info("notification_handler_bot_updated")
    else:
        logger.warning("notification_handler_not_initialized")


def cleanup_event_handlers() -> None:
    """Clear all event handlers."""
    dispatcher = get_event_dispatcher()
    dispatcher.clear()
    logger.info("event_handlers_cleared")

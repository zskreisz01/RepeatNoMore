"""Event dispatcher for pub/sub pattern in RepeatNoMore."""

import asyncio
from collections import defaultdict
from functools import lru_cache
from typing import Callable, Coroutine, Any, Optional

from app.events.types import DocumentEvent, EventData
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for event handlers
EventHandler = Callable[[EventData], Coroutine[Any, Any, None]]


class EventDispatcher:
    """
    Event dispatcher implementing pub/sub pattern.

    Allows handlers to subscribe to specific event types and
    dispatches events to all registered handlers asynchronously.
    """

    def __init__(self):
        """Initialize the event dispatcher."""
        self._handlers: dict[DocumentEvent, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        logger.info("event_dispatcher_initialized")

    def subscribe(
        self,
        event_type: DocumentEvent,
        handler: EventHandler,
    ) -> None:
        """
        Subscribe a handler to a specific event type.

        Args:
            event_type: The event type to subscribe to
            handler: Async function to handle the event
        """
        self._handlers[event_type].append(handler)
        logger.debug(
            "handler_subscribed",
            event_type=event_type.value,
            handler=handler.__name__,
        )

    def subscribe_all(self, handler: EventHandler) -> None:
        """
        Subscribe a handler to all event types.

        Args:
            handler: Async function to handle all events
        """
        self._global_handlers.append(handler)
        logger.debug("global_handler_subscribed", handler=handler.__name__)

    def unsubscribe(
        self,
        event_type: DocumentEvent,
        handler: EventHandler,
    ) -> bool:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove

        Returns:
            True if handler was removed, False if not found
        """
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)
            logger.debug(
                "handler_unsubscribed",
                event_type=event_type.value,
                handler=handler.__name__,
            )
            return True
        return False

    async def emit(self, event: EventData) -> list[Exception]:
        """
        Emit an event to all subscribed handlers.

        Args:
            event: The event data to dispatch

        Returns:
            List of exceptions from failed handlers (empty if all succeeded)
        """
        handlers = self._handlers.get(event.event_type, []) + self._global_handlers
        errors: list[Exception] = []

        if not handlers:
            logger.debug("no_handlers_for_event", event_type=event.event_type.value)
            return errors

        logger.info(
            "event_emitted",
            event_type=event.event_type.value,
            handler_count=len(handlers),
            source=event.source,
        )

        # Run all handlers concurrently
        tasks = [self._safe_call(handler, event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
                logger.error(
                    "handler_failed",
                    event_type=event.event_type.value,
                    error=str(result),
                )

        return errors

    async def _safe_call(
        self,
        handler: EventHandler,
        event: EventData,
    ) -> Optional[Exception]:
        """
        Safely call a handler, catching any exceptions.

        Args:
            handler: The handler to call
            event: The event data

        Returns:
            None on success, Exception on failure
        """
        try:
            await handler(event)
            logger.debug(
                "handler_completed",
                event_type=event.event_type.value,
                handler=handler.__name__,
            )
            return None
        except Exception as e:
            logger.error(
                "handler_exception",
                event_type=event.event_type.value,
                handler=handler.__name__,
                error=str(e),
            )
            return e

    def clear(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()
        self._global_handlers.clear()
        logger.info("event_dispatcher_cleared")


# Global instance
_event_dispatcher: Optional[EventDispatcher] = None


@lru_cache()
def get_event_dispatcher() -> EventDispatcher:
    """
    Get or create the global event dispatcher instance.

    Returns:
        EventDispatcher: The event dispatcher singleton
    """
    global _event_dispatcher
    if _event_dispatcher is None:
        _event_dispatcher = EventDispatcher()
    return _event_dispatcher

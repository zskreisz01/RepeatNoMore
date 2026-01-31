"""Event capture utility for testing event emissions."""

from typing import Optional

from app.events.types import DocumentEvent, EventData
from app.events.dispatcher import EventDispatcher


class EventCapture:
    """
    Utility class for capturing and verifying events in tests.

    Usage:
        event_capture = EventCapture()
        event_capture.start_capture(dispatcher)

        # ... run code that emits events ...

        captured = event_capture.get_events(DocumentEvent.DRAFT_CREATED)
        assert len(captured) == 1

        event_capture.stop_capture(dispatcher)
    """

    def __init__(self) -> None:
        """Initialize the event capture."""
        self.events: list[EventData] = []
        self._original_emit = None
        self._dispatcher: Optional[EventDispatcher] = None

    def start_capture(self, dispatcher: EventDispatcher) -> None:
        """
        Start capturing events from the dispatcher.

        Args:
            dispatcher: The event dispatcher to capture from
        """
        self._dispatcher = dispatcher
        self._original_emit = dispatcher.emit

        async def capture_emit(event: EventData) -> list[Exception]:
            """Capture event and call original emit."""
            self.events.append(event)
            return await self._original_emit(event)

        dispatcher.emit = capture_emit

    def stop_capture(self, dispatcher: EventDispatcher) -> None:
        """
        Stop capturing and restore original emit method.

        Args:
            dispatcher: The event dispatcher to restore
        """
        if self._original_emit is not None:
            dispatcher.emit = self._original_emit
            self._original_emit = None
            self._dispatcher = None

    def get_events(
        self, event_type: Optional[DocumentEvent] = None
    ) -> list[EventData]:
        """
        Get captured events, optionally filtered by type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            List of captured events
        """
        if event_type is not None:
            return [e for e in self.events if e.event_type == event_type]
        return list(self.events)

    def clear(self) -> None:
        """Clear all captured events."""
        self.events.clear()

    def assert_event_emitted(
        self,
        event_type: DocumentEvent,
        count: int = 1,
        **kwargs,
    ) -> None:
        """
        Assert that an event was emitted with specific attributes.

        Args:
            event_type: The expected event type
            count: Expected number of events (default: 1)
            **kwargs: Additional attributes to check on the event

        Raises:
            AssertionError: If expectations are not met
        """
        events = self.get_events(event_type)
        assert len(events) == count, (
            f"Expected {count} {event_type.value} events, got {len(events)}"
        )

        if kwargs and events:
            for event in events:
                for key, expected_value in kwargs.items():
                    # Check direct attributes first
                    actual_value = getattr(event, key, None)
                    # Fall back to metadata
                    if actual_value is None:
                        actual_value = event.metadata.get(key)

                    assert actual_value == expected_value, (
                        f"Event {key}: expected {expected_value}, got {actual_value}"
                    )

    def assert_no_events(self, event_type: Optional[DocumentEvent] = None) -> None:
        """
        Assert that no events were emitted.

        Args:
            event_type: Optional event type to check (all events if None)

        Raises:
            AssertionError: If any matching events were captured
        """
        events = self.get_events(event_type)
        event_desc = event_type.value if event_type else "any type"
        assert len(events) == 0, (
            f"Expected no events of {event_desc}, got {len(events)}"
        )

    def get_last_event(
        self, event_type: Optional[DocumentEvent] = None
    ) -> Optional[EventData]:
        """
        Get the last captured event.

        Args:
            event_type: Optional event type to filter by

        Returns:
            Last captured event or None
        """
        events = self.get_events(event_type)
        return events[-1] if events else None

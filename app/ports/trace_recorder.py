"""TraceRecorder port — abstract interface for recording agent events."""

from __future__ import annotations

from typing import Any, Protocol


class TraceRecorder(Protocol):
    """Emit structured trace events for debugging and integration tests."""

    def record(self, event_name: str, payload: dict[str, Any]) -> None:
        """Record a named event with an arbitrary payload dict."""
        ...


class NoOpTraceRecorder:
    """A TraceRecorder that silently discards all events.

    Used as the default in production when no tracing backend is configured.
    """

    def record(self, event_name: str, payload: dict[str, Any]) -> None:
        pass

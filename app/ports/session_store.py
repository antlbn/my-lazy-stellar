"""SessionStore port — abstract interface for persisting conversation sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Session:
    """A single conversation session between a user and the assistant."""

    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)


class SessionStore(Protocol):
    """Load and save sessions keyed by session_id."""

    def load(self, session_id: str) -> Session | None:
        """Return the session, or None if it does not exist."""
        ...

    def save(self, session: Session) -> None:
        """Persist the session (create or overwrite)."""
        ...


class SessionStoreError(Exception):
    """Raised when a session store operation fails."""

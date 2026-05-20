from app.ports.session_store import Session, SessionStore


class InMemorySessionStore(SessionStore):
    """Simple dict-backed session store for local dev and testing."""

    def __init__(self) -> None:
        self._store: dict[str, Session] = {}

    def load(self, session_id: str) -> Session | None:
        return self._store.get(session_id)

    def save(self, session: Session) -> None:
        self._store[session.session_id] = session

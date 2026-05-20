"""SearchProvider port — abstract interface for finding stargazing spots."""

from __future__ import annotations

from typing import Protocol

from app.domain.models import StargazingSpot, UserContext


class SearchProvider(Protocol):
    """Search the internet for candidate stargazing spots."""

    def find_spots(self, query: str, ctx: UserContext) -> list[StargazingSpot]:
        """Return a list of candidate spots matching the query and user context.

        Args:
            query: Natural-language search query (location + constraints).
            ctx:   Structured user context (transport, radius, etc.).

        Returns:
            A (possibly empty) list of StargazingSpot objects.

        Raises:
            SearchProviderError: if the search service is unavailable.
        """
        ...


class SearchProviderError(Exception):
    """Raised when a search provider fails."""

from collections.abc import Callable

from duckduckgo_search import DDGS
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import Capability

from core.models import StargazingSpot, UserContext


def default_search_fn(query: str, context: UserContext) -> list[StargazingSpot]:
    """A minimal DuckDuckGo search implementation for MVP."""
    spots = []
    with DDGS() as ddgs:
        # Build search query from context
        full_query = f"{query} stargazing spots near {context.location}"
        if context.transport:
            full_query += f" accessible by {context.transport}"

        results = list(ddgs.text(full_query, max_results=3))
        for r in results:
            spots.append(
                StargazingSpot(
                    name=r.get("title", "Unknown Spot"),
                    latitude=0.0,  # Mock coords for text search
                    longitude=0.0,
                    source=r.get("href", ""),
                    description=r.get("body", ""),
                    accessibility="See description",
                    safety_assessment="Unknown",
                )
            )
    return spots


class SearchCapability(Capability):
    def __init__(
        self,
        search_fn: Callable[[str, UserContext], list[StargazingSpot]] | None = None,
    ):
        self._search = search_fn or default_search_fn

    def register(self, agent: Agent) -> None:
        @agent.tool
        def search_spots(
            ctx: RunContext,
            query: str,
            location: str,
            transport: str | None = None,
            radius_km: float | None = None,
            has_telescope: bool | None = None,
            time_window: str | None = None,
        ) -> list[StargazingSpot]:
            """Find candidate stargazing spots based on user context. Use this whenever you need to discover locations."""
            user_context = UserContext(
                location=location,
                transport=transport,
                radius_km=radius_km,
                has_telescope=has_telescope,
                time_window=time_window,
            )
            return self._search(query, user_context)

from collections.abc import Callable

from duckduckgo_search import DDGS
from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AgentToolset

from core.models import StargazingSpot, UserContext


def default_search_fn(query: str, context: UserContext) -> list[StargazingSpot] | str:
    """A resilient search implementation that uses Tavily if an API key is present,
    falling back to DuckDuckGo, and reporting errors gracefully if both fail."""
    import os
    import httpx
    import logfire
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    full_query = f"{query} stargazing spots near {context.location}"
    if context.transport:
        full_query += f" accessible by {context.transport}"
        
    spots = []
    
    if tavily_key:
        logfire.info("Using Tavily Search API for active query: {query}", query=full_query)
        try:
            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_key,
                    "query": full_query,
                    "max_results": 3,
                },
                timeout=8.0
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            for r in results:
                spots.append(
                    StargazingSpot(
                        name=r.get("title", "Unknown Spot"),
                        latitude=48.8566,  # Default fallback coords for weather API
                        longitude=2.3522,
                        source=r.get("url", ""),
                        description=r.get("content", ""),
                        accessibility="See description / source",
                        safety_assessment="Unknown",
                        bortle_class=4,
                    )
                )
            return spots
        except Exception as e:
            logfire.exception("Tavily search failed: {error}", error=str(e))
            return (
                f"Error: Tavily Search API failed (details: {e}). "
                "Please verify your TAVILY_API_KEY in the .env file or try again later."
            )
            
    # Fallback to DuckDuckGo
    logfire.info("Tavily API key not found. Falling back to DuckDuckGo search.")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(full_query, max_results=3))
            for r in results:
                spots.append(
                    StargazingSpot(
                        name=r.get("title", "Unknown Spot"),
                        latitude=48.8566,
                        longitude=2.3522,
                        source=r.get("href", ""),
                        description=r.get("body", ""),
                        accessibility="Accessible by car/public transport",
                        safety_assessment="Safe public open area",
                        bortle_class=4,
                    )
                )
    except Exception as e:
        logfire.exception("DuckDuckGo search failed: {error}", error=str(e))
        return (
            f"Error: The default DuckDuckGo search service is temporarily rate-limited or unavailable (details: {e}). "
            "To solve this issue permanently and enable highly reliable web searches, please sign up for a free "
            "Tavily Search API key (takes 30 seconds at https://tavily.com) and add it to your .env file as: "
            "TAVILY_API_KEY=your_tavily_key"
        )
            
    return spots


class SearchCapability(AbstractCapability[None]):
    def __init__(
        self,
        search_fn: Callable[[str, UserContext], list[StargazingSpot] | str] | None = None,
    ) -> None:
        self._search = search_fn or default_search_fn

    @classmethod
    def get_serialization_name(cls) -> str | None:
        return None

    def get_toolset(self) -> AgentToolset[None]:
        toolset = FunctionToolset[None]()

        @toolset.tool
        def search_spots(
            ctx: RunContext[None],
            query: str,
            location: str,
            transport: str | None = None,
            radius_km: float | None = None,
            has_telescope: bool | None = None,
            time_window: str | None = None,
        ) -> list[StargazingSpot] | str:
            """Find candidate stargazing spots based on user context. Returns list of spots or an error description string if the search service fails."""
            user_context = UserContext(
                location=location,
                transport=transport,
                radius_km=radius_km,
                has_telescope=has_telescope,
                time_window=time_window,
            )
            return self._search(query, user_context)

        return toolset

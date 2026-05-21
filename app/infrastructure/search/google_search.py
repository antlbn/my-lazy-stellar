import json
import logging
from typing import Any

from duckduckgo_search import DDGS
from pydantic_ai import Agent

from app.domain.models import StargazingSpot, UserContext
from app.ports.search_provider import SearchProvider, SearchProviderError

logger = logging.getLogger(__name__)


class LLMSearchProvider(SearchProvider):
    """Uses a web search tool and an LLM to extract structured StargazingSpots."""

    def __init__(self, model: Any) -> None:
        self.parsing_agent = Agent(
            model=model,
            output_type=list[StargazingSpot],
            system_prompt=(
                "You are an expert data extractor. Given raw search results, extract 3-5 "
                "stargazing spots that match the user's constraints. Return them as a structured list. "
                "Ensure that latitude and longitude are floats, and provide an accessibility/safety assessment."
            ),
        )

    def find_spots(self, query: str, ctx: UserContext) -> list[StargazingSpot]:
        try:
            logger.info("Executing web search for: %s", query)
            # DDGS().text() returns a list of dicts with 'title', 'href', 'body'
            results = DDGS().text(query, max_results=10)
            raw_results = json.dumps(results, indent=2)
        except Exception as e:
            raise SearchProviderError(f"Search tool failed: {e}") from e

        prompt = (
            f"User constraints: Transport={ctx.transport or 'Any'}, "
            f"Radius={ctx.radius_km or 'Any'}, Telescope={'Yes' if ctx.has_telescope else 'No'}\n\n"
            f"Search Results:\n{raw_results}"
        )

        try:
            result = self.parsing_agent.run_sync(prompt)
            return result.output
        except Exception as e:
            raise SearchProviderError(f"Failed to parse LLM response into spots: {e}") from e

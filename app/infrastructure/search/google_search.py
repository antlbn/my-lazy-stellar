import json
import logging
from pathlib import Path
from typing import Any

from langchain_community.tools import DuckDuckGoSearchRun

from app.domain.models import StargazingSpot, UserContext
from app.ports.llm_provider import LLMProvider
from app.ports.search_provider import SearchProvider, SearchProviderError

logger = logging.getLogger(__name__)


class LLMSearchProvider(SearchProvider):
    """Uses a web search tool and an LLM to extract structured StargazingSpots."""

    def __init__(self, llm: LLMProvider, search_tool: Any = None) -> None:
        self.llm = llm
        self.search_tool = search_tool or DuckDuckGoSearchRun()

        # Load the prompt template from the prompts directory
        prompt_path = (
            Path(__file__).parent.parent.parent / "prompts" / "search_agent.md"
        )
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text(encoding="utf-8")
        else:
            self.prompt_template = "Return a JSON array of spots based on: {query}. Search results: {raw_results}"

    def find_spots(self, query: str, ctx: UserContext) -> list[StargazingSpot]:
        try:
            logger.info("Executing web search for: %s", query)
            raw_results = self.search_tool.invoke(query)
        except Exception as e:
            raise SearchProviderError(f"Search tool failed: {e}") from e

        prompt = self.prompt_template.format(
            query=query,
            raw_results=raw_results,
            transport=ctx.transport or "Any",
            radius=ctx.radius_km or "Any",
            telescope="Yes" if ctx.has_telescope else "No",
        )

        reply = self.llm.chat([{"role": "user", "content": prompt}])

        return self._parse_json(reply)

    def _parse_json(self, reply: str) -> list[StargazingSpot]:
        try:
            cleaned = reply.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            data = json.loads(cleaned.strip())
            spots = []
            for item in data:
                spots.append(
                    StargazingSpot(
                        name=item.get("name", "Unknown"),
                        latitude=float(item.get("latitude", 0.0)),
                        longitude=float(item.get("longitude", 0.0)),
                        source=item.get("source", "Search"),
                        description=item.get("description", ""),
                        accessibility=item.get("accessibility", "Unknown"),
                        safety_assessment=item.get("safety_assessment", "Unknown"),
                        bortle_class=item.get("bortle_class"),
                    )
                )
            return spots
        except Exception as e:
            raise SearchProviderError(
                f"Failed to parse LLM response into spots: {e}\nResponse: {reply}"
            ) from e

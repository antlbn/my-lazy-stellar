from dataclasses import dataclass
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model

from app.application.responses import ChatAgentOutput
from app.domain.models import StargazingSpot, UserContext, WeatherReport
from app.ports.search_provider import SearchProvider
from app.ports.weather_provider import WeatherProvider


@dataclass(frozen=True)
class AgentDeps:
    """Runtime capabilities available to PydanticAI tools."""

    search: SearchProvider
    weather: WeatherProvider


class PydanticAIOrchestrator:
    """Thin application-facing wrapper around the PydanticAI agent.

    The rest of the application should depend on this small wrapper, not on
    PydanticAI's Agent/RunContext APIs directly.
    """

    def __init__(
        self,
        *,
        model: Model | str,
        search: SearchProvider,
        weather: WeatherProvider,
        system_prompt: str | None = None,
    ) -> None:
        self.deps = AgentDeps(search=search, weather=weather)
        self.agent = Agent(
            model=model,
            deps_type=AgentDeps,
            output_type=ChatAgentOutput,
            system_prompt=system_prompt or _load_main_prompt(),
        )
        self._register_tools()

    def handle(
        self,
        *,
        session_id: str,
        messages: list[dict[str, str]],
    ) -> ChatAgentOutput:
        """Run the agent for the latest user message.

        Session persistence remains owned by ChatUseCase. This method only
        translates application messages into the first PydanticAI run shape.
        Rich message-history conversion will be added when we wire sessions.
        """
        user_prompt = _latest_user_message(messages)
        result = self.agent.run_sync(
            user_prompt,
            deps=self.deps,
            conversation_id=session_id,
        )
        return result.output

    def _register_tools(self) -> None:
        @self.agent.tool
        def search_spots(
            ctx: RunContext[AgentDeps],
            query: str,
            location: str,
            transport: str | None = None,
            radius_km: float | None = None,
            has_telescope: bool | None = None,
            safety_concerns: str | None = None,
            time_window: str | None = None,
        ) -> list[StargazingSpot]:
            """Find 3-5 candidate stargazing spots for the user's constraints."""
            user_context = UserContext(
                location=location,
                transport=transport,
                radius_km=radius_km,
                has_telescope=has_telescope,
                safety_concerns=safety_concerns,
                time_window=time_window,
            )
            return ctx.deps.search.find_spots(query, user_context)

        @self.agent.tool
        def get_astro_weather(
            ctx: RunContext[AgentDeps],
            latitude: float,
            longitude: float,
        ) -> WeatherReport | None:
            """Fetch astronomy weather for a candidate spot."""
            try:
                return ctx.deps.weather.get_astro_weather(latitude, longitude)
            except Exception:
                return None


def _load_main_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "main_agent.md"
    return prompt_path.read_text(encoding="utf-8")


def _latest_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""

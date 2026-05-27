from dataclasses import dataclass

from pydantic_ai import Agent

from agent import create_agent
from pydantic_ai.capabilities import WebSearch
from capabilities.weather import WeatherCapability

from .bootstrap import configure_logfire, initialize_storage
from .settings import Settings, load_settings


@dataclass
class Runtime:
    settings: Settings
    agent: Agent[None, str]

    def close(self) -> None:
        """Close runtime-owned resources.

        The current MVP opens DuckDuckGo, HTTP, and SQLite connections per call.
        Keeping an explicit close hook prevents those resources from spreading
        into entrypoints when persistent clients are introduced later.
        """


def create_runtime(*, settings: Settings | None = None) -> Runtime:
    resolved_settings = settings or load_settings()
    configure_logfire(resolved_settings)
    initialize_storage(resolved_settings)

    agent = create_agent(
        model=resolved_settings.model,
        capabilities=[
            WebSearch(local=False),
            WeatherCapability(),
        ],
    )
    return Runtime(settings=resolved_settings, agent=agent)

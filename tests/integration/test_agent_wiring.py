from pydantic_ai import FunctionToolset

from agent import create_agent
from capabilities.search import SearchCapability
from capabilities.weather import WeatherCapability


def test_agent_imports_with_configured_output_type() -> None:
    agent = create_agent()

    assert agent.output_type is str


def test_search_capability_exposes_search_toolset() -> None:
    toolset = SearchCapability(search_fn=lambda query, context: []).get_toolset()

    assert isinstance(toolset, FunctionToolset)
    assert "search_spots" in toolset.tools


def test_weather_capability_exposes_weather_toolset() -> None:
    toolset = WeatherCapability(
        weather_fn=lambda latitude, longitude: None
    ).get_toolset()

    assert isinstance(toolset, FunctionToolset)
    assert "get_astro_weather" in toolset.tools

from collections.abc import Callable

import httpx
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import Capability

from core.models import WeatherReport


def default_weather_fn(latitude: float, longitude: float) -> WeatherReport | None:
    """Fetch astronomy weather from 7timer API."""
    url = f"http://www.7timer.info/bin/astro.php?lon={longitude}&lat={latitude}&ac=0&unit=metric&output=json&tzshift=0"
    try:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()

        # Parse first few data points
        dataseries = data.get("dataseries", [])
        if not dataseries:
            return None

        cloud_cover = {i: ds.get("cloudcover", 9) for i, ds in enumerate(dataseries)}
        transparency = {i: ds.get("transparency", 1) for i, ds in enumerate(dataseries)}
        wind_speed = {
            i: ds.get("wind10m", {}).get("speed", 1) for i, ds in enumerate(dataseries)
        }
        temperature = {i: float(ds.get("temp2m", 0)) for i, ds in enumerate(dataseries)}

        return WeatherReport(
            cloud_cover=cloud_cover,
            transparency=transparency,
            wind_speed=wind_speed,
            temperature=temperature,
            seeing=dataseries[0].get("seeing"),
            raw_response=data,
        )
    except Exception:
        return None


class WeatherCapability(Capability):
    def __init__(
        self, weather_fn: Callable[[float, float], WeatherReport | None] | None = None
    ):
        self._weather = weather_fn or default_weather_fn

    def register(self, agent: Agent) -> None:
        @agent.tool
        def get_astro_weather(
            ctx: RunContext, latitude: float, longitude: float
        ) -> WeatherReport | None:
            """Fetch astronomy weather (cloud cover, transparency) for a specific coordinate."""
            return self._weather(latitude, longitude)

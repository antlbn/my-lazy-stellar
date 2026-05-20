"""WeatherProvider port — abstract interface for astronomy weather."""

from __future__ import annotations

from typing import Protocol

from app.domain.models import WeatherReport


class WeatherProvider(Protocol):
    """Fetch astronomy-oriented weather for a geographic coordinate."""

    def get_astro_weather(self, lat: float, lon: float) -> WeatherReport:
        """Return a WeatherReport for the given coordinates.

        Raises:
            WeatherProviderError: if the underlying service is unavailable.
        """
        ...


class WeatherProviderError(Exception):
    """Raised when a weather provider fails to return a usable result."""

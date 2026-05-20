import logging

from app.domain.models import WeatherReport
from app.ports.weather_provider import WeatherProvider, WeatherProviderError

logger = logging.getLogger(__name__)


class FallbackWeatherProvider(WeatherProvider):
    """Tries a primary weather provider, falling back to a secondary on error."""

    def __init__(self, primary: WeatherProvider, fallback: WeatherProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    def get_astro_weather(self, lat: float, lon: float) -> WeatherReport:
        try:
            return self.primary.get_astro_weather(lat, lon)
        except WeatherProviderError as e:
            logger.warning("Primary weather provider failed: %s. Using fallback.", e)
            return self.fallback.get_astro_weather(lat, lon)

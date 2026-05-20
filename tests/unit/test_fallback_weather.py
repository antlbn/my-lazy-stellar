from app.domain.models import WeatherReport
from app.infrastructure.weather.fallback_weather import FallbackWeatherProvider
from app.ports.weather_provider import WeatherProvider, WeatherProviderError


class BrokenWeather(WeatherProvider):
    def get_astro_weather(self, lat: float, lon: float) -> WeatherReport:
        raise WeatherProviderError("API Down")


class WorkingWeather(WeatherProvider):
    def get_astro_weather(self, lat: float, lon: float) -> WeatherReport:
        return WeatherReport(1, 2, 3.0, 4.0)


def test_fallback_weather_uses_primary() -> None:
    primary = WorkingWeather()
    secondary = BrokenWeather()

    fallback = FallbackWeatherProvider(primary, secondary)
    report = fallback.get_astro_weather(10.0, 20.0)
    assert report.cloud_cover == 1


def test_fallback_weather_uses_fallback_on_error() -> None:
    primary = BrokenWeather()
    secondary = WorkingWeather()

    fallback = FallbackWeatherProvider(primary, secondary)
    report = fallback.get_astro_weather(10.0, 20.0)
    assert report.cloud_cover == 1

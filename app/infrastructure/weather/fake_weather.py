from app.domain.models import WeatherReport
from app.ports.weather_provider import WeatherProvider


class FakeWeatherProvider(WeatherProvider):
    """A deterministic weather provider for unit testing."""

    def __init__(self, cloud_cover: int = 1, transparency: int = 7) -> None:
        self.cloud_cover = cloud_cover
        self.transparency = transparency

    def get_astro_weather(self, lat: float, lon: float) -> WeatherReport:
        return WeatherReport(
            cloud_cover=self.cloud_cover,
            transparency=self.transparency,
            wind_speed=10.0,
            temperature=15.0,
            seeing=1,
            raw_response={"source": "fake_weather_provider"},
        )

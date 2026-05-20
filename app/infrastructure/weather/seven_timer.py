import json
import urllib.parse
import urllib.request

from app.domain.models import WeatherReport
from app.ports.weather_provider import WeatherProvider, WeatherProviderError

SEVEN_TIMER_API_URL = "https://www.7timer.info/bin/api.pl"


class SevenTimerWeatherProvider(WeatherProvider):
    """Adapter for the 7timer astronomy weather API."""

    def get_astro_weather(self, lat: float, lon: float) -> WeatherReport:
        params = urllib.parse.urlencode(
            {"lon": lon, "lat": lat, "product": "astro", "output": "json"}
        )
        url = f"{SEVEN_TIMER_API_URL}?{params}"

        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.load(response)
        except Exception as exc:
            raise WeatherProviderError(f"7timer request failed: {exc}") from exc

        # 7timer returns a 'dataseries' list. We extract the first 3-hour step.
        if not data or "dataseries" not in data or not data["dataseries"]:
            raise WeatherProviderError("Invalid response format from 7timer")

        current = data["dataseries"][0]

        return WeatherReport(
            cloud_cover=current.get("cloudcover", 9),
            transparency=current.get("transparency", 1),
            wind_speed=current.get("wind10m", {}).get("speed", 9.0),
            temperature=current.get("temp2m", 0.0),
            seeing=current.get("seeing", None),
            raw_response=data,
        )

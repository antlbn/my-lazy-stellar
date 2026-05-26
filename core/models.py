from __future__ import annotations
from pydantic import BaseModel, Field


class StargazingSpot(BaseModel):
    name: str = Field(description="Name of the stargazing spot")
    latitude: float = Field(description="Latitude coordinate", ge=-90, le=90)
    longitude: float = Field(description="Longitude coordinate", ge=-180, le=180)
    source: str = Field(description="URL source or origin of the recommendation")
    description: str = Field(description="Description of the spot, including highlights or unique features")
    accessibility: str = Field(description="Details on how to access the spot (road quality, walking required)")
    safety_assessment: str = Field(description="Safety assessment of the location (wildlife, steep drops, etc.)")
    timezone_offset: float = Field(description="UTC timezone offset in hours")
    bortle_class: int | None = Field(default=None, description="Bortle Dark Sky Scale (1-9), where 1 is the darkest")
    additional_info: str | None = Field(default=None, description="Any other additional info")
    time_of_discovery: str | None = Field(default=None, description="When the spot was discovered/logged")
    seasonal_nature_risks: str | None = Field(default=None, description="Seasonal nature risks (snow blocks, high tides, etc.)")


class UserContext(BaseModel):
    location: str = Field(description="Desired location or area for stargazing")
    transport: str | None = Field(default=None, description="Mode of transport (e.g. 'car', 'public transit')")
    radius_km: float | None = Field(default=None, description="Search radius in kilometers")
    has_telescope: bool | None = Field(default=None, description="Whether the user has a telescope")
    fear_of_wildlife: bool | None = Field(default=None, description="Whether the user is afraid of wildlife")
    special_requirements: str | None = Field(default=None, description="Any other special requirements")
    accessibility_needs: str | None = Field(default=None, description="Accessibility needs or physical limitations")
    safety_concerns: str | None = Field(default=None, description="Specific safety concerns")
    time_window: str | None = Field(default=None, description="Preferred time window or date for stargazing")


class Recommendation(BaseModel):
    spot: StargazingSpot = Field(description="The recommended stargazing spot")
    weather: WeatherReport | None = Field(default=None, description="Weather report for this spot")
    suitability_score: float = Field(default=0.0, description="Calculated suitability score")
    notes: str | None = Field(default=None, description="Specific notes or recommendations for the user")


#------------------------------------------------------------------------------------
# contract models for weather capability - agent 
#-----------------------------------------------------------------------------------

# This LocationQuery model are a helper contract to ask the Weather capability for weather report

class LocationQuery(BaseModel):
    name: str = Field(description="Name of the location")
    latitude: float = Field(description="Latitude coordinate", ge=-90, le=90)
    longitude: float = Field(description="Longitude coordinate", ge=-180, le=180)
    timezone_offset: float = Field(description="UTC timezone offset in hours for the location")

# HourlyForecast are helper contract for weather tool, it contains meteo- and astro-parameters for one specific time point of the forecast.
class HourlyForecast(BaseModel):
    """Метео- и астро-параметры для одной конкретной временной точки прогноза."""

    time: str = Field(
        description="Local time of the forecast point formatted as 'MM-DD HH:00'."
    )
    cloud_cover: int = Field(
        description="Cloud cover. Scale 1-9: 1 is clear sky, 9 is completely overcast."
    )
    transparency: int = Field(
        description="Atmospheric transparency. Scale 1-8: 1 is best, 8 is worst."
    )
    seeing: int = Field(
        description="Astronomical seeing (stability). Scale 1-8: 1 is best, 8 is worst."
    )
    lifted_index: int = Field(
        description="Atmospheric instability index (Lifted Index). >=2 is stable, <=-4 is unstable."
    )
    wind_speed: int = Field(
        description="Wind speed scale (1-8)."
    )
    wind_direction: str = Field(
        description="Wind direction compass points (e.g., 'N', 'SW')."
    )
    temperature: float = Field(
        description="Temperature in degrees Celsius."
    )
    humidity: int = Field(
        description="Relative humidity in percentage."
    )
    precipitation: str = Field(
        description="Precipitation type (e.g., 'none', 'rain', 'snow')."
    )

# WeatherReport contract for weather tool, it contains weather report with hourly forecasts for the night-time windows.
class WeatherReport(BaseModel):
    """Прогноз погоды с шагом 3 часа.

    Содержит отфильтрованные точки для ночного окна (~21:00 до ~09:00 по местному времени).
    """

    name: str | None = Field(default=None, description="Name of the location")
    latitude: float = Field(description="Latitude coordinate", ge=-90, le=90)
    longitude: float = Field(description="Longitude coordinate", ge=-180, le=180)

    # Hourly forecasts for the night time window
    forecasts: list[HourlyForecast] = Field(
        default_factory=list,
        description="List of hourly forecasts for the night-time windows."
    )

    # --- Metadata ---
    sunset_time: str | None = Field(default=None, description="Sunset time, if available")
    sunrise_time: str | None = Field(default=None, description="Sunrise time, if available")
    special_description: str | None = Field(default=None, description="Special description or alerts")
    raw_response: dict = Field(default_factory=dict, description="Raw source API response", exclude=True)

    # ------------------------------------------------------------------
    # Methods that can be usefull further for evaluating the weather for the night. 
    # ------------------------------------------------------------------

    def first_forecast(self) -> HourlyForecast | None:
       """returns first forecast from forecasts list"""
       return self.forecasts[0] if self.forecasts else None

from pydantic import BaseModel, Field

class StargazingSpot(BaseModel):
    name: str = Field(description="Name of the stargazing spot")
    latitude: float = Field(description="Latitude coordinate")
    longitude: float = Field(description="Longitude coordinate")
    source: str = Field(description="URL source or origin of the recommendation")
    description: str = Field(description="Description of the spot, including highlights or unique features")
    accessibility: str = Field(description="Details on how to access the spot (road quality, walking required)")
    safety_assessment: str = Field(description="Safety assessment of the location (wildlife, steep drops, etc.)")
    timezone_offset: float | None = Field(default=0.0, description="UTC timezone offset in hours")
    bortle_class: int | None = Field(default=None, description="Bortle Dark Sky Scale (1-9), where 1 is the darkest")
    additional_info: str | None = Field(default=None, description="Any other additional info")
    time_of_discovery: str | None = Field(default=None, description="When the spot was discovered/logged")
    seasonal_nature_risks: str | None = Field(default=None, description="Seasonal nature risks (snow blocks, high tides, etc.)")


class WeatherReport(BaseModel):
    """Прогноз погоды с шагом 3 часа.

    Все словари индексированы локальным временем в формате "MM-DD HH:00".
    Ночное окно: записи с ~21:00 до ~09:00 (сумерки → рассвет).
    """

    name: str | None = Field(default=None, description="Name of the location")
    latitude: float = Field(default=0.0, description="Latitude coordinate")
    longitude: float = Field(default=0.0, description="Longitude coordinate")

    # --- Ключевые астро-параметры, ключ = "MM-DD HH:00" (локальное время) ---
    cloud_cover: dict[str, int] = Field(
        default_factory=dict,
        description="Cloud cover. Scale 1-9: 1 is clear sky, 9 is completely overcast."
    )
    transparency: dict[str, int] = Field(
        default_factory=dict,
        description="Atmospheric transparency. Scale 1-8: 1 is best, 8 is worst."
    )
    seeing: dict[str, int] = Field(
        default_factory=dict,
        description="Astronomical seeing (stability). Scale 1-8: 1 is best, 8 is worst."
    )
    lifted_index: dict[str, int] = Field(
        default_factory=dict,
        description="Atmospheric instability index (Lifted Index). >=2 is stable, <=-4 is unstable."
    )

    # --- Метео-параметры, ключ = "MM-DD HH:00" (локальное время) ---
    wind_speed: dict[str, int] = Field(
        default_factory=dict,
        description="Wind speed scale (1-8)."
    )
    wind_direction: dict[str, str] = Field(
        default_factory=dict,
        description="Wind direction compass points (e.g., 'N', 'SW')."
    )
    temperature: dict[str, float] = Field(
        default_factory=dict,
        description="Temperature in degrees Celsius."
    )
    humidity: dict[str, int] = Field(
        default_factory=dict,
        description="Relative humidity in percentage."
    )
    precipitation: dict[str, str] = Field(
        default_factory=dict,
        description="Precipitation type (e.g., 'none', 'rain', 'snow')."
    )

    # --- Метаданные ---
    sunset_time: str | None = Field(default=None, description="Sunset time, if available")
    sunrise_time: str | None = Field(default=None, description="Sunrise time, if available")
    special_description: str | None = Field(default=None, description="Special description or alerts")
    raw_response: dict = Field(default_factory=dict, description="Raw source API response", exclude=True)

    # ------------------------------------------------------------------
    # Удобные методы для получения «текущего» значения
    # (первая запись в отфильтрованном ночном окне)
    # ------------------------------------------------------------------

    def _first_value(self, mapping: dict, default):
        """Возвращает первое значение из словаря или default."""
        return next(iter(mapping.values()), default)

    def cloud_cover_now(self) -> int:
        """Облачность первой точки прогноза (1=ясно, 9=пасмурно)."""
        return self._first_value(self.cloud_cover, 9)

    def transparency_now(self) -> int:
        """Прозрачность первой точки прогноза."""
        return self._first_value(self.transparency, 1)

    def seeing_now(self) -> int:
        """Сиинг первой точки прогноза."""
        return self._first_value(self.seeing, 1)


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

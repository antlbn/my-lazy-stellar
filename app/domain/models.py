from dataclasses import dataclass, field


@dataclass
class StargazingSpot:
    name: str
    latitude: float
    longitude: float
    source: str
    description: str
    accessibility: str
    safety_assessment: str
    bortle_class: int | None = None
    additional_info: str | None = None


@dataclass
class WeatherReport:
    cloud_cover: int  # 0 to 9: 0 is completely clear, 9 is fully overcast
    transparency: int  # transparency index (from 7timer)
    wind_speed: float  # wind index/speed
    temperature: float  # temperature in Celsius
    seeing: int | None = None
    raw_response: dict = field(default_factory=dict)


@dataclass
class UserContext:
    location: str
    transport: str | None = None
    radius_km: float | None = None
    has_telescope: bool | None = None
    fear_of_wildlife: bool | None = None
    safety_concerns: str | None = None
    time_window: str | None = None


@dataclass
class Recommendation:
    spot: StargazingSpot
    weather: WeatherReport | None = None
    suitability_score: float = 0.0
    notes: str | None = None

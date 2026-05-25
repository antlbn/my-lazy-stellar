from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StargazingSpot:
    name: str
    latitude: float
    longitude: float
    source: str
    description: str
    accessibility: str
    safety_assessment: str
    timezone_offset: float  # Смещение относительно UTC в часах
    bortle_class: int | None = None
    additional_info: str | None = None
    time_of_discovery: str | None = None
    seasonal_nature_risks: str | None = None


#пока не буду расширять модель всякими примочками - остановлюсь на этом, если чтото придумую буду дописывать коментарии сюда 



@dataclass
class WeatherReport:
    """Прогноз погоды с шагом 3 часа.

    Все словари индексированы временем в формате "HH:00" (UTC),
    что соответствует реальному времени точки прогноза.
    Ночное окно: записи с ~21:00 до ~09:00 (сумерки → рассвет).
    """

    name: str | None = None
    latitude: float = 0.0
    longitude: float = 0.0

    # --- Ключевые астро-параметры, ключ = "MM-DD HH:00" (UTC) ---
    cloud_cover: dict[str, int] = field(default_factory=dict)   # 1–9: 1=ясно, 9=сплошная облачность
    transparency: dict[str, int] = field(default_factory=dict)  # 1–8: прозрачность атмосферы
    seeing: dict[str, int] = field(default_factory=dict)        # 1–8: астрономический сиинг
    lifted_index: dict[str, int] = field(default_factory=dict)  # индекс атм. нестабильности: ≥2=стабильно, ≤-4=нестабильно

    # --- Метео-параметры, ключ = "MM-DD HH:00" (UTC) ---
    wind_speed: dict[str, int] = field(default_factory=dict)    # 1–8: балл скорости ветра
    wind_direction: dict[str, str] = field(default_factory=dict) # стороны света: "N", "SW" и т.д.
    temperature: dict[str, float] = field(default_factory=dict) # температура, °C
    humidity: dict[str, int] = field(default_factory=dict)      # относительная влажность, %
    precipitation: dict[str, str] = field(default_factory=dict) # тип осадков: "none", "rain" и т.д.

    # --- Метаданные ---
    sunset_time: str | None = None
    sunrise_time: str | None = None
    special_description: str | None = None
    raw_response: dict = field(default_factory=dict)

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


@dataclass
class UserContext:
    location: str
    transport: str | None = None
    radius_km: float | None = None
    has_telescope: bool | None = None
    fear_of_wildlife: bool | None = None
    special_requirements: str | None = None
    accessibility_needs: str | None = None
    safety_concerns: str | None = None
    time_window: str | None = None


@dataclass
class Recommendation:
    spot: StargazingSpot
    weather: WeatherReport | None = None
    suitability_score: float = 0.0
    notes: str | None = None

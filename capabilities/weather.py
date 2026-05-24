import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import httpx
from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AgentToolset

from core.models import WeatherReport

logger = logging.getLogger(__name__)

# Общий HTTP-клиент (thread-safe, переиспользуемый)
_http_client = httpx.Client(timeout=5.0)

# Ночное окно наблюдений: часы UTC, которые нас интересуют.
# Берём вечер → ранее утро (сумерки + ночь + рассвет).
_NIGHT_HOURS = set(range(21, 24)) | set(range(0, 10))  # 21, 22, 23, 0 … 9

# Формат метки времени в поле "init" от 7timer: YYYYMMDDHH
_INIT_FORMAT = "%Y%m%d%H"


def default_weather_fn(
    *, name: str, latitude: float, longitude: float, timezone_offset: float
) -> WeatherReport | None:
    """Получить астрономический прогноз с 7timer и вернуть WeatherReport.

    Возвращает только ночное окно (~21:00–09:00 по местному времени).
    Точки за пределами отбрасываются. Все словари индексированы локальным временем.
    """

    # ── 1. Валидация координат ────────────────────────────────────────────
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        logger.warning("Невалидные координаты: lat=%s, lon=%s", latitude, longitude)
        return None

    # ── 2. Запрос к API 7timer (product=astro) ────────────────────────────
    url = (
        "http://www.7timer.info/bin/astro.php"
        f"?lon={longitude}&lat={latitude}"
        "&ac=0&unit=metric&output=json&tzshift=0"
    )
    try:
        response = _http_client.get(url)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.error("HTTP-ошибка при запросе погоды (%s, %s): %s", latitude, longitude, exc)
        return None

    # ── 3. Парсинг init-метки → базовый datetime (UTC) ───────────────────
    # Поле «init» имеет формат YYYYMMDDHH, например "2026052406"
    raw_init = data.get("init", "")
    try:
        base_time = datetime.strptime(raw_init, _INIT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        logger.error("Не удалось разобрать init='%s'", raw_init)
        return None

    # ── 4. Фильтрация: оставляем текущую/ближайшую ночь и следующую ────────
    # Используем явно переданное снаружи смещение часового пояса
    local_tz = timezone(timedelta(hours=timezone_offset))

    dataseries = data.get("dataseries", [])
    if not dataseries:
        logger.debug("Пустой dataseries для %s, %s", latitude, longitude)
        return None

    # Фильтруем прошедшие точки относительно текущего времени (с допуском 2 часа),
    # чтобы не «цепляться» за ушедшую ночь, если прогноз старый.
    now = datetime.now(timezone.utc)
    is_live = (now - base_time) < timedelta(hours=24)

    nights = {}
    for point in dataseries:
        point_time_utc = base_time + timedelta(hours=point["timepoint"])
        point_time_local = point_time_utc.astimezone(local_tz)

        if is_live and point_time_utc < now - timedelta(hours=2):
            continue

        # Проверяем попадание в ночные часы уже по МЕСТНОМУ времени
        if point_time_local.hour not in _NIGHT_HOURS:
            continue

        # Дату ночи определяем тоже по местному времени
        if point_time_local.hour >= 21:
            night_date = point_time_local.date()
        else:
            night_date = (point_time_local - timedelta(days=1)).date()

        nights.setdefault(night_date, []).append((point_time_local, point))

    if not nights:
        logger.debug("Нет ночных точек для %s, %s (init=%s)", latitude, longitude, raw_init)
        return None

    # Берем первую (текущую/ближайшую) ночь и следующую за ней (всего до 2 ночей).
    # Даже если первая ночь - это только "огрызок" (например, пара утренних часов), 
    # мы всё равно получим полные данные для следующей ночи.
    target_night_dates = sorted(nights.keys())[:2]

    night_points = []
    for night_date in target_night_dates:
        for point_time_local, point in nights[night_date]:
            # Ключ теперь в локальном времени!
            time_key = point_time_local.strftime("%m-%d %H:00")
            night_points.append((time_key, point))

    # ── 5. Сборка словарей по каждому параметру ───────────────────────────
    # Ключ везде — строка «HH:00» (UTC). Порядок соответствует порядку API.

    cloud_cover:    dict[str, int]   = {}
    transparency:   dict[str, int]   = {}
    seeing:         dict[str, int]   = {}
    lifted_index:   dict[str, int]   = {}
    wind_speed:     dict[str, int]   = {}
    wind_direction: dict[str, str]   = {}
    temperature:    dict[str, float] = {}
    humidity:       dict[str, int]   = {}
    precipitation:  dict[str, str]   = {}

    for time_key, point in night_points:
        cloud_cover[time_key]    = point.get("cloudcover", 9)
        transparency[time_key]   = point.get("transparency", 1)
        seeing[time_key]         = point.get("seeing", 1)
        lifted_index[time_key]   = point.get("lifted_index", 0)
        wind_speed[time_key]     = point.get("wind10m", {}).get("speed", 0)
        wind_direction[time_key] = point.get("wind10m", {}).get("direction", "N")
        temperature[time_key]    = float(point.get("temp2m", 0))
        humidity[time_key]       = point.get("rh2m", 0)
        precipitation[time_key]  = point.get("prec_type", "none")

    # ── 6. Сборка и возврат WeatherReport ────────────────────────────────
    return WeatherReport(
        name=name,
        latitude=latitude,
        longitude=longitude,
        cloud_cover=cloud_cover,
        transparency=transparency,
        seeing=seeing,
        lifted_index=lifted_index,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        temperature=temperature,
        humidity=humidity,
        precipitation=precipitation,
        raw_response=data,
    )


class WeatherCapability(AbstractCapability[None]):
    def __init__(
        self, weather_fn: Callable[..., WeatherReport | None] | None = None
    ) -> None:
        self._weather = weather_fn or default_weather_fn

    @classmethod
    def get_serialization_name(cls) -> str | None:
        return None

    def get_toolset(self) -> AgentToolset[None]:
        toolset = FunctionToolset[None]()

        @toolset.tool
        def get_astro_weather(
            ctx: RunContext[None], name: str, latitude: float, longitude: float, timezone_offset: float
        ) -> WeatherReport | None:
            """Fetch astronomy weather (cloud cover, transparency) for a specific coordinate.
            `timezone_offset` is the UTC offset in hours for the coordinate location.
            """
            return self._weather(
                name=name, 
                latitude=latitude, 
                longitude=longitude, 
                timezone_offset=timezone_offset
            )

        return toolset

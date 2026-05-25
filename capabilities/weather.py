import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone

import httpx
from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AgentToolset

from core.models import WeatherReport

logger = logging.getLogger(__name__)

# Общий HTTP-клиент (thread-safe, переиспользуемый)
_http_client = httpx.Client(timeout=5.0)

# Ночное окно наблюдений по местному времени: вечер → раннее утро.
_NIGHT_HOURS = set(range(21, 24)) | set(range(0, 10))  # 21, 22, 23, 0 … 9

# Формат метки времени в поле "init" от 7timer: YYYYMMDDHH
_INIT_FORMAT = "%Y%m%d%H"


# ── Слой 1: I/O ──────────────────────────────────────────────────────────────
# Единственное место, которое знает про HTTP и про 7timer.
# Всё остальное получает уже готовый dict.

def fetch_astro_raw(
    latitude: float,
    longitude: float,
    client: httpx.Client,
) -> dict | None:
    """Сделать HTTP-запрос к 7timer и вернуть сырой JSON как dict.

    Возвращает None при любой сетевой или HTTP-ошибке.
    Никакой бизнес-логики здесь нет — только транспорт.
    """
    url = (
        "http://www.7timer.info/bin/astro.php"
        f"?lon={longitude}&lat={latitude}"
        "&ac=0&unit=metric&output=json&tzshift=0"
    )
    try:
        response = client.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        logger.error("HTTP-ошибка при запросе погоды (%s, %s): %s", latitude, longitude, exc)
        return None


# ── Слой 2: чистая логика (pure function) ────────────────────────────────────
# Принимает данные, возвращает данные. Никакого I/O, никакого datetime.now().
# Тестируется без моков — просто передаёшь dict и datetime.

def parse_night_points(
    data: dict,
    timezone_offset: float,
    now: datetime,
) -> list[tuple[str, dict]]:
    """Отфильтровать dataseries и вернуть точки ближайших двух ночей.

    Каждая точка — кортеж (time_key, raw_point), где time_key —
    строка вида «MM-DD HH:00» в локальном времени.

    Правила отбора:
    - Часы 21:00–23:59 и 00:00–09:59 по местному времени.
    - Если прогноз «живой» (init < 24 ч назад) — прошедшие точки пропускаем
      (допуск 2 ч, чтобы не терять текущий час).
    - Берём максимум 2 ночи: текущую (или ближайшую) и следующую.
    """
    # 1. Разбираем init-метку
    raw_init = data.get("init", "")
    try:
        base_time = datetime.strptime(raw_init, _INIT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        logger.error("Не удалось разобрать init='%s'", raw_init)
        return []

    dataseries = data.get("dataseries", [])
    if not dataseries:
        logger.debug("Пустой dataseries (init=%s)", raw_init)
        return []

    local_tz = timezone(timedelta(hours=timezone_offset))
    is_live = (now - base_time) < timedelta(hours=24)

    # 2. Группируем точки по «дате ночи»
    nights: dict[date, list[tuple[datetime, dict]]] = {}
    for point in dataseries:
        point_utc   = base_time + timedelta(hours=point["timepoint"])
        point_local = point_utc.astimezone(local_tz)

        # Пропускаем уже прошедшее (с допуском)
        if is_live and point_utc < now - timedelta(hours=2):
            continue

        # Только ночные часы по местному времени
        if point_local.hour not in _NIGHT_HOURS:
            continue

        # Вечерние часы (≥ 21:00) относим к той же дате,
        # утренние (< 10:00) — к предыдущей: так вся ночь под одним ключом.
        if point_local.hour >= 21:
            night_date = point_local.date()
        else:
            night_date = (point_local - timedelta(days=1)).date()

        nights.setdefault(night_date, []).append((point_local, point))

    if not nights:
        logger.debug("Нет ночных точек (init=%s)", raw_init)
        return []

    # 3. Берём первые две ночи и выстраиваем плоский список
    target_dates = sorted(nights.keys())[:2]
    result: list[tuple[str, dict]] = []
    for night_date in target_dates:
        for point_local, point in nights[night_date]:
            time_key = point_local.strftime("%m-%d %H:00")
            result.append((time_key, point))

    return result


# ── Слой 3: маппинг → модель ─────────────────────────────────────────────────
# Знает только о структуре WeatherReport. Никакого HTTP, никакой фильтрации.

def build_weather_report(
    name: str,
    latitude: float,
    longitude: float,
    night_points: list[tuple[str, dict]],
    raw_response: dict,
) -> WeatherReport:
    """Собрать WeatherReport из отфильтрованных точек.

    Ключ каждого словаря — строка «MM-DD HH:00» (локальное время).
    """
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
        raw_response=raw_response,
    )


# ── Оркестратор (публичный вход) ─────────────────────────────────────────────
# Тонкий «клей»: валидация + вызов трёх слоёв по очереди.
# Все зависимости инъектируемы — тесты могут подменить любую из них.

def default_weather_fn(
    *,
    name: str,
    latitude: float,
    longitude: float,
    timezone_offset: float,
    client: httpx.Client = _http_client,   # подменяется в тестах
    now: datetime | None = None,           # подменяется в тестах
) -> WeatherReport | None:
    """Получить астрономический прогноз и вернуть WeatherReport.

    Возвращает только ночное окно (~21:00–09:00 по местному времени).
    """
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        logger.warning("Невалидные координаты: lat=%s, lon=%s", latitude, longitude)
        return None

    now = now or datetime.now(timezone.utc)

    raw = fetch_astro_raw(latitude, longitude, client)
    if raw is None:
        return None

    night_points = parse_night_points(raw, timezone_offset, now)
    if not night_points:
        return None

    return build_weather_report(name, latitude, longitude, night_points, raw)


# ── Capability для агента ─────────────────────────────────────────────────────

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
                timezone_offset=timezone_offset,
            )

        return toolset

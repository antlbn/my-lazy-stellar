import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from types import TracebackType
from typing import Any

import httpx
from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.toolsets import AgentToolset

from core.models import HourlyForecast, LocationQuery, WeatherReport

logger = logging.getLogger(__name__)

# Night observation window in local time: evening → early morning.
_NIGHT_HOURS = set(range(21, 24)) | set(range(0, 10))  # 21, 22, 23, 0 … 9

# Timestamp format in the "init" field from 7timer: YYYYMMDDHH
_INIT_FORMAT = "%Y%m%d%H"


# ── Layer 1: I/O ──────────────────────────────────────────────────────────────
# The only component aware of HTTP and 7timer.
# All other functions receive pre-parsed dictionaries.

def fetch_astro_raw(
    latitude: float,
    longitude: float,
    client: httpx.Client,
) -> dict | None:
    """Make HTTP request to 7timer and return raw JSON as dict.

    Returns None on any network or HTTP error.
    Contains no business logic — only transport.
    """
    url = (
        "https://www.7timer.info/bin/astro.php"
        f"?lon={longitude}&lat={latitude}"
        "&ac=0&unit=metric&output=json&tzshift=0"
    )
    try:
        response = client.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        logger.error("HTTP error querying weather (%s, %s): %s", latitude, longitude, exc)
        return None


# ── Layer 2: Pure Logic (pure function) ────────────────────────────────────
# Accepts data, returns data. No I/O, no datetime.now().
# Testable without mocks — simply pass a dict and datetime.

def parse_night_points(
    data: dict,
    timezone_offset: float,
    now: datetime,
) -> list[tuple[str, dict]]:
    """Filter dataseries and return points for the nearest two nights.

    Each point is a tuple (time_key, raw_point), where time_key is
    a string like "MM-DD HH:00" in local time.

    Selection rules:
    - Hours 21:00–23:59 and 00:00–09:59 local time.
    - If forecast is "live" (init < 24 hours ago) — skip past points
      (with a 2-hour tolerance so current hour isn't immediately lost).
    - Limit to at most 2 nights: current (or nearest) and next.
    """
    # 1. Parse the init timestamp
    raw_init = data.get("init", "")
    try:
        base_time = datetime.strptime(raw_init, _INIT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        logger.error("Could not parse init='%s'", raw_init)
        return []

    dataseries = data.get("dataseries", [])
    if not dataseries:
        logger.debug("Empty dataseries (init=%s)", raw_init)
        return []

    local_tz = timezone(timedelta(hours=timezone_offset))
    is_live = (now - base_time) < timedelta(hours=24)

    # 2. Group points by "night date"
    nights: dict[date, list[tuple[datetime, dict]]] = {}
    for point in dataseries:
        point_utc   = base_time + timedelta(hours=point["timepoint"])
        point_local = point_utc.astimezone(local_tz)

        # Skip points already in the past (with tolerance)
        if is_live and point_utc < now - timedelta(hours=2):
            continue

        # Night hours only in local time
        if point_local.hour not in _NIGHT_HOURS:
            continue

        # Group evening hours (>= 21:00) with the same calendar date,
        # and morning hours (< 10:00) with the previous date to keep the night coherent.
        if point_local.hour >= 21:
            night_date = point_local.date()
        else:
            night_date = (point_local - timedelta(days=1)).date()

        nights.setdefault(night_date, []).append((point_local, point))

    if not nights:
        logger.debug("No night points found (init=%s)", raw_init)
        return []

    # 3. Take the first two nights and flatten the list
    target_dates = sorted(nights.keys())[:2]
    result: list[tuple[str, dict]] = []
    for night_date in target_dates:
        for point_local, point in nights[night_date]:
            time_key = point_local.strftime("%m-%d %H:00")
            result.append((time_key, point))

    return result


# ── Layer 3: Mapping → Model ─────────────────────────────────────────────────
# Knows only about the structure of WeatherReport. No HTTP, no filtering logic.

def build_weather_report(
    name: str,
    latitude: float,
    longitude: float,
    night_points: list[tuple[str, dict]],
    raw_response: dict,
) -> WeatherReport:
    """Build WeatherReport from filtered night points.

    Key for each forecast point is a string "MM-DD HH:00" in local time.
    """
    forecasts = [
        HourlyForecast(
            time=time_key,
            cloud_cover=point.get("cloudcover", 9),
            transparency=point.get("transparency", 1),
            seeing=point.get("seeing", 1),
            lifted_index=point.get("lifted_index", 0),
            wind_speed=point.get("wind10m", {}).get("speed", 0),
            wind_direction=point.get("wind10m", {}).get("direction", "N"),
            temperature=float(point.get("temp2m", 0)),
            humidity=point.get("rh2m", 0),
            precipitation=point.get("prec_type", "none"),
        )
        for time_key, point in night_points
    ]

    return WeatherReport(
        name=name,
        latitude=latitude,
        longitude=longitude,
        forecasts=forecasts,
        raw_response=raw_response,
    )


# ── Orchestrator (Public Entrypoint) ─────────────────────────────────────────────
# Glue layer: triggers validation and calls the three layers sequentially.
# Dependencies are fully injectible for testing.

def default_weather_fn(
    *,
    name: str,
    latitude: float,
    longitude: float,
    timezone_offset: float,
    client: httpx.Client | None = None,
    now: datetime | None = None,
) -> WeatherReport | None:
    """Fetch astronomy forecast and return a WeatherReport.

    Returns only the night-time stargazing windows (~21:00 to ~09:00 local time).

    Args:
        client: HTTP client to use. When None a short-lived client is created
            for this call only. Prefer passing a persistent client (e.g. from
            WeatherCapability) to reuse the connection pool.
    """
    now = now or datetime.now(timezone.utc)

    if client is not None:
        raw = fetch_astro_raw(latitude, longitude, client)
    else:
        with httpx.Client(timeout=5.0) as _tmp:
            raw = fetch_astro_raw(latitude, longitude, _tmp)

    if raw is None:
        return None

    night_points = parse_night_points(raw, timezone_offset, now)
    if not night_points:
        return None

    return build_weather_report(name, latitude, longitude, night_points, raw)


# ── Capability for Agent ─────────────────────────────────────────────────────

class WeatherCapability(AbstractCapability[Any]):
    """Capability that provides astronomical weather forecasts for stargazing.

    Owns an httpx.Client for the duration of its lifetime.
    Use as a context manager for guaranteed cleanup::

        with WeatherCapability() as cap:
            agent = Agent(..., capabilities=[cap])
            ...
    """

    def __init__(
        self,
        weather_fn: Callable[..., WeatherReport | None] | None = None,
        *,
        http_timeout: float = 5.0,
    ) -> None:
        self._client = httpx.Client(timeout=http_timeout)
        # Bind the client into a closure so default_weather_fn always uses
        # this instance's client, not a module-level singleton.
        if weather_fn is not None:
            self._weather = weather_fn
        else:
            _client = self._client
            def _bound_weather_fn(**kwargs: object) -> WeatherReport | None:
                return default_weather_fn(client=_client, **kwargs)  # type: ignore[arg-type]
            self._weather = _bound_weather_fn

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> "WeatherCapability":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    @classmethod
    def get_serialization_name(cls) -> str | None:
        return None

    def get_toolset(self) -> AgentToolset[Any]:
        toolset = FunctionToolset[Any]()

        @toolset.tool
        def get_astro_weather(
            ctx: RunContext[Any],
            locations: list[LocationQuery],
        ) -> dict[str, WeatherReport | str]:
            """Fetch astronomy weather (cloud cover, transparency, seeing, wind, temp) for multiple locations.

            This tool fetches night-time stargazing weather parameters for all requested locations in parallel.

            Args:
                locations: A list of locations containing name, latitude, longitude, and timezone_offset.

            Returns:
                dict[str, WeatherReport | str]: A dictionary mapping each location name to its WeatherReport or an error message string.
            """
            results = {}

            def _fetch_one(loc: LocationQuery) -> tuple[str, WeatherReport | str]:
                
                try:
                    report = self._weather(
                        name=loc.name,
                        latitude=loc.latitude,
                        longitude=loc.longitude,
                        timezone_offset=loc.timezone_offset,
                    )
                    if report is None:
                        return loc.name, f"Error: Weather data not available for '{loc.name}'. The API may be down, or no night-time forecast points were found."
                    return loc.name, report
                except Exception as e:
                    return loc.name, f"Error: Failed to retrieve weather: {e}"

            # Fetch weather for all locations in parallel using a thread pool
            with ThreadPoolExecutor(max_workers=min(len(locations), 10)) as executor:
                for name, res in executor.map(_fetch_one, locations):
                    results[name] = res

            return results

        return toolset

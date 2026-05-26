from core.models import HourlyForecast, Recommendation, StargazingSpot, UserContext, WeatherReport
from core.policies import (
    enough_context_to_search,
    rank_spots,
    weather_acceptable,
    weather_poor,
)


def _weather(cloud_cover: int, transparency: int) -> WeatherReport:
    return WeatherReport(
        forecasts=[
            HourlyForecast(
                time="05-26 22:00",
                cloud_cover=cloud_cover,
                transparency=transparency,
                seeing=1,
                lifted_index=0,
                wind_speed=5,
                wind_direction="N",
                temperature=12.0,
                humidity=50,
                precipitation="none",
            )
        ]
    )


def _spot(name: str) -> StargazingSpot:
    return StargazingSpot(
        name=name,
        latitude=48.2,
        longitude=16.37,
        source="test",
        description="Test spot",
        accessibility="Unknown",
        safety_assessment="Unknown",
    )


def test_weather_acceptability_uses_cloud_cover_and_transparency() -> None:
    assert weather_acceptable(_weather(cloud_cover=2, transparency=3))
    assert not weather_acceptable(_weather(cloud_cover=4, transparency=3))
    assert not weather_acceptable(_weather(cloud_cover=2, transparency=1))


def test_missing_weather_does_not_block_search() -> None:
    assert weather_acceptable(None)
    assert not weather_poor(None)


def test_weather_poor_flags_only_clearly_bad_cloud_cover() -> None:
    assert not weather_poor(_weather(cloud_cover=5, transparency=3))
    assert weather_poor(_weather(cloud_cover=6, transparency=3))


def test_enough_context_requires_non_empty_location() -> None:
    assert enough_context_to_search(UserContext(location="Vienna"))
    assert not enough_context_to_search(UserContext(location=" "))


def test_rank_spots_prefers_better_weather_then_base_score() -> None:
    cloudy = Recommendation(
        spot=_spot("Cloudy"),
        weather=_weather(cloud_cover=6, transparency=4),
        suitability_score=5.0,
    )
    clear = Recommendation(
        spot=_spot("Clear"),
        weather=_weather(cloud_cover=1, transparency=4),
        suitability_score=1.0,
    )

    assert [rec.spot.name for rec in rank_spots([cloudy, clear])] == [
        "Clear",
        "Cloudy",
    ]

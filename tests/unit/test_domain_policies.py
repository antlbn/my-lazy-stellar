from app.domain.models import Recommendation, StargazingSpot, UserContext, WeatherReport
from app.domain.policies import enough_context_to_search, rank_spots, weather_acceptable


def test_enough_context_to_search() -> None:
    assert enough_context_to_search(UserContext(location="Paris")) is True
    assert enough_context_to_search(UserContext(location="  ")) is False
    assert enough_context_to_search(UserContext(location="")) is False


def test_weather_acceptable() -> None:
    # Cloud cover <= 3 is acceptable, transparency >= 2 is acceptable
    good = WeatherReport(
        cloud_cover=2, transparency=3, wind_speed=10.0, temperature=15.0
    )
    assert weather_acceptable(good) is True

    bad_clouds = WeatherReport(
        cloud_cover=6, transparency=3, wind_speed=10.0, temperature=15.0
    )
    assert weather_acceptable(bad_clouds) is False

    # None is treated as acceptable to avoid blocking searches if weather data is missing
    assert weather_acceptable(None) is True


def test_rank_spots() -> None:
    spot1 = StargazingSpot("A", 1.0, 1.0, "src", "desc", "acc", "safe")
    spot2 = StargazingSpot("B", 2.0, 2.0, "src", "desc", "acc", "safe")

    rec_bad = Recommendation(spot=spot1, weather=WeatherReport(8, 1, 10.0, 10.0))
    rec_good = Recommendation(spot=spot2, weather=WeatherReport(1, 4, 10.0, 10.0))

    ranked = rank_spots([rec_bad, rec_good])

    # "B" should be ranked higher due to much better weather
    assert ranked[0].spot.name == "B"

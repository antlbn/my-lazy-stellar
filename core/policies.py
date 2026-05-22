from __future__ import annotations

from .models import Recommendation, UserContext, WeatherReport

# Weather policy thresholds
CLOUD_COVER_MAX_ACCEPTABLE = 3  # 0-9 scale; <=3 is acceptable, >5 is bad
CLOUD_COVER_MAX_POOR = 5
TRANSPARENCY_MIN_ACCEPTABLE = 2  # 7timer transparency: higher is better (1-7)
WIND_MAX_ACCEPTABLE_KMH = 30.0


def weather_acceptable(report: WeatherReport | None) -> bool:
    """Return True if the weather is good enough for stargazing."""
    if report is None:
        return True  # no data → don't block search
    return (
        report.cloud_cover_now() <= CLOUD_COVER_MAX_ACCEPTABLE
        and report.transparency_now() >= TRANSPARENCY_MIN_ACCEPTABLE
    )


def weather_poor(report: WeatherReport | None) -> bool:
    """Return True if the weather is clearly bad (cloud cover > 5)."""
    if report is None:
        return False
    return report.cloud_cover_now() > CLOUD_COVER_MAX_POOR


def enough_context_to_search(ctx: UserContext) -> bool:
    """Return True when the agent has enough user context to kick off a search."""
    return bool(ctx.location and ctx.location.strip())


def rank_spots(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Sort recommendations by suitability: better weather & score first.
    The function is deterministic and free of LLM calls.
    """

    def _score(rec: Recommendation) -> tuple[float, int, int]:
        score = rec.suitability_score
        w = rec.weather
        if w is not None:
            if w.cloud_cover_now() <= CLOUD_COVER_MAX_ACCEPTABLE:
                score += 3.0
            if w.transparency_now() >= TRANSPARENCY_MIN_ACCEPTABLE:
                score += 2.0
            if w.cloud_cover_now() > CLOUD_COVER_MAX_POOR:
                score -= 1.0
            return score, -w.cloud_cover_now(), w.transparency_now()
        return score, 0, 0

    return sorted(recommendations, key=_score, reverse=True)

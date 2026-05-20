"""
Domain policies — pure Python, zero external dependencies.

These functions encode the core business rules of Lazy Stellar:
  - when we have enough context from the user to start searching;
  - whether a weather report is acceptable for stargazing;
  - how to rank a list of recommendations (deterministic heuristic).
"""

from __future__ import annotations

from app.domain.models import Recommendation, UserContext, WeatherReport

# ---------------------------------------------------------------------------
# Weather policy thresholds (from product spec)
# ---------------------------------------------------------------------------
CLOUD_COVER_MAX_ACCEPTABLE = 3  # 0-9 scale; ≤3 is acceptable, >5 is bad
CLOUD_COVER_MAX_POOR = 5  # above this → poor conditions

TRANSPARENCY_MIN_ACCEPTABLE = 2  # 7timer transparency: higher is better (1-7)
WIND_MAX_ACCEPTABLE_KMH = 30.0  # km/h equivalent; >30 is uncomfortable


def weather_acceptable(report: WeatherReport | None) -> bool:
    """Return True if the weather is good enough for stargazing.

    Accepts None gracefully (treated as unknown / skip weather gate).
    """
    if report is None:
        return True  # no data → don't block search
    return (
        report.cloud_cover <= CLOUD_COVER_MAX_ACCEPTABLE
        and report.transparency >= TRANSPARENCY_MIN_ACCEPTABLE
    )


def weather_poor(report: WeatherReport | None) -> bool:
    """Return True if the weather is clearly bad (cloud cover > 5)."""
    if report is None:
        return False
    return report.cloud_cover > CLOUD_COVER_MAX_POOR


def enough_context_to_search(ctx: UserContext) -> bool:
    """Return True when the agent has enough user context to kick off a search.

    Minimum requirement: a non-empty location string.
    Everything else is optional; the search agent will include general notes
    when transport / radius are absent.
    """
    return bool(ctx.location and ctx.location.strip())


def rank_spots(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Sort recommendations by suitability: better weather & score first.

    Scoring heuristic (all additive, higher is better):
      +3  if cloud_cover <= CLOUD_COVER_MAX_ACCEPTABLE
      +2  if transparency >= TRANSPARENCY_MIN_ACCEPTABLE
      -1  if cloud_cover >  CLOUD_COVER_MAX_POOR
      +suitability_score   (set by the LLM ranking node)

    The function is deterministic and free of LLM calls.
    """

    def _score(rec: Recommendation) -> float:
        score = rec.suitability_score
        w = rec.weather
        if w is not None:
            if w.cloud_cover <= CLOUD_COVER_MAX_ACCEPTABLE:
                score += 3.0
            if w.transparency >= TRANSPARENCY_MIN_ACCEPTABLE:
                score += 2.0
            if w.cloud_cover > CLOUD_COVER_MAX_POOR:
                score -= 1.0
        return score

    return sorted(recommendations, key=_score, reverse=True)

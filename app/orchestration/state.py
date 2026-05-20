import operator
from typing import Annotated

from typing_extensions import TypedDict

from app.domain.models import Recommendation, StargazingSpot, UserContext


def update_spots(
    left: list[StargazingSpot], right: list[StargazingSpot]
) -> list[StargazingSpot]:
    """Replace the list of spots entirely."""
    return right


def update_recommendations(
    left: list[Recommendation], right: list[Recommendation]
) -> list[Recommendation]:
    """Replace the list of recommendations entirely."""
    return right


class AstroState(TypedDict):
    """The state dictionary for our LangGraph orchestrator."""

    session_id: str
    messages: Annotated[list[dict[str, str]], operator.add]
    context: UserContext
    spots: Annotated[list[StargazingSpot], update_spots]
    recommendations: Annotated[list[Recommendation], update_recommendations]
    final_answer: str

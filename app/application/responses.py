from dataclasses import dataclass

from pydantic import BaseModel, Field


class RecommendedSpotOutput(BaseModel):
    """Structured recommendation returned by the agent."""

    name: str
    latitude: float
    longitude: float
    source: str
    description: str
    weather_summary: str
    accessibility: str
    safety_assessment: str
    rank_reason: str
    bortle_class: int | None = None


class ChatAgentOutput(BaseModel):
    """Structured PydanticAI result used by the application layer."""

    answer: str
    recommendations: list[RecommendedSpotOutput] = Field(
        default_factory=list, max_length=5
    )
    assumptions: list[str] = Field(default_factory=list)
    follow_up_question: str | None = None


@dataclass
class AssistantResponse:
    """The final response sent back to the presentation layer."""

    text: str
    agent_output: ChatAgentOutput | None = None

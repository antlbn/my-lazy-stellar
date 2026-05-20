from dataclasses import dataclass


@dataclass
class AssistantResponse:
    """The final response sent back to the presentation layer."""

    text: str

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import AbstractCapability


class SpotReport(BaseModel):
    """Structured summary produced when the agent has found stargazing spots.

    The agent should call ``report_spots`` only after it has gathered enough
    context from the user AND completed the search/weather workflow.
    During the initial clarification phase the agent must NOT call this tool —
    it should simply respond with a plain conversational message.
    """

    spots_found: int
    summary: str  # human-readable markdown summary for the user


# PydanticAI model strings include the provider prefix. For OpenRouter model IDs,
# use: openrouter:<openrouter-model-id>
DEFAULT_MODEL = "openrouter:nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
DEFAULT_SYSTEM_PROMPT = "You are Lazy Stellar, a stargazing assistant."


def load_system_prompt(
    prompt_path: Path | None = None,
    fallback: str = DEFAULT_SYSTEM_PROMPT,
) -> str:
    path = prompt_path or Path(__file__).parent / "prompts" / "main_agent.md"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return fallback


def create_agent(
    *,
    model: str = DEFAULT_MODEL,
    capabilities: Sequence[AbstractCapability[None]] = (),
    system_prompt: str | None = None,
) -> Agent[None, str]:
    # No output_type — the agent replies with plain conversational text.
    # When it has found spots it calls the `report_spots` tool instead.
    agent: Agent[None, str] = Agent(
        model=model,
        defer_model_check=True,
        capabilities=list(capabilities),
    )

    prompt = system_prompt if system_prompt is not None else load_system_prompt()

    @agent.system_prompt
    def get_system_prompt() -> str:
        return prompt

    @agent.tool_plain
    def report_spots(report: SpotReport) -> str:
        """Call this tool ONLY when you have completed the full search workflow and
        are ready to present the final ranked list of stargazing spots to the user.
        Do NOT call this tool to ask clarifying questions — just reply with text.
        """
        # The tool return value is fed back to the model as a tool result.
        # The model will then produce its final conversational reply using it.
        return (
            f"[spots_found={report.spots_found}] "
            f"Report recorded. Now present the following summary to the user:\n\n"
            f"{report.summary}"
        )

    return agent

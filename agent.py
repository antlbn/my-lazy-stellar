from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.capabilities import AbstractCapability


class AssistantResponse(BaseModel):
    message: str
    spots_found: int
    clarification_needed: bool


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
) -> Agent[None, AssistantResponse]:
    agent = Agent(
        model=model,
        output_type=AssistantResponse,
        defer_model_check=True,
        capabilities=list(capabilities),
    )

    prompt = system_prompt if system_prompt is not None else load_system_prompt()

    @agent.system_prompt
    def get_system_prompt() -> str:
        return prompt

    return agent

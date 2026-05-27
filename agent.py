import os
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import AbstractCapability
from pydantic_ai.capabilities import WebSearch

from core.models import StargazingSpot, UserContext


LAZY_STELLAR_MODEL = os.getenv("LAZY_STELLAR_MODEL", "openrouter:google/gemini-3.1-flash-lite")

class SpotSearchReport(BaseModel):
    spots_found: int = Field(description="Number of spots returned by the search tool.")
    summary: str = Field(description="Concise user-facing answer in English.")
    spots: list[StargazingSpot] = Field(default_factory=list)


agent_spot_searcher = Agent(
    model=LAZY_STELLAR_MODEL,
    defer_model_check=True,
    deps_type=UserContext,
    capabilities=[
        WebSearch(local=False),
    ],
    output_type=SpotSearchReport,
    instructions=(
        "You are a search assistant. Your ONLY job is to search for stargazing spots.\n\n"
        "SPOT SEARCH:\n"
        "Use the web search tool to find stargazing spots for the user's location. "
        "Collect at least 2-5 concrete spots with coordinates and descriptions. "
        "Do not invent spots not returned by the tool. "
        "If search fails, set spots_found=0, spots=[], and put the error in summary.\n\n"
        "FINAL OUTPUT:\n"
        "Return SpotSearchReport containing the found spots."
    ),
)


@agent_spot_searcher.instructions
def inject_user_context(ctx: RunContext[UserContext]) -> str:
    """Inject structured UserContext into the prompt so the LLM has all search parameters."""
    return f"User context:\n{ctx.deps.model_dump_json(indent=2, exclude_none=True)}"


# PydanticAI model strings include the provider prefix. For OpenRouter model IDs,
# use: openrouter:<openrouter-model-id>
DEFAULT_MODEL = "openrouter:google/gemini-3.1-flash-lite"
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
    agent: Agent[None, str] = Agent(
        model=model,
        defer_model_check=True,
        capabilities=list(capabilities),
    )

    prompt = system_prompt if system_prompt is not None else load_system_prompt()

    @agent.system_prompt
    def get_system_prompt() -> str:
        return prompt

    @agent.tool
    async def search_spots(ctx: RunContext[None], context: UserContext) -> SpotSearchReport:
        """Search for candidate stargazing locations using the user's preferences.
        Call this tool in Phase 2 once you have collected the user's location and preferences.
        """
        result = await agent_spot_searcher.run(
            "Please find stargazing spots based on my context.",
            deps=context,
        )
        return result.output

    return agent

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import AbstractCapability

from capabilities.weather import WeatherCapability


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



#The sub-agent that performs the spot searching based on user crieteria. 
# Ones it has comleted the search, it will return the structured report.

# Class for structured result of search_spot sub-agent (Pydantic BaseModel)
@dataclass
class SpotSearchReport(BaseModel):
    spots_found: int
    spots: list[StargazingSpot] = field(default_factory=list)

agent_spot_searcher = Agent(
    model=LAZY_STELLAR_MODEL,
    defer_model_check=True,
    capabilities=[SearchCapability()],
    deps_type=None,
    output_type: [SpotSearchReport]
)

@agent_spot_searcher.system_prompt
def get_spot_searcher_system_prompt() -> str:
    return (
        "You are a helpful assistant that searches the web for stargazing spots. "
        "When given a user query, your task is to find and summarize relevant information "
        "about stargazing locations. You should return a structured report with the number of spots found "
        "and a markdown summary of the best locations. Use the `report_spots` tool to return your findings."
    )

@agent_spot_searcher.tool_plain
def report_spots(report: SpotReport) -> str:
    """This tool is used by the spot searcher agent to report the results of its search.

    The agent should call this tool ONLY after it has completed its search and is ready to present
    the final findings. The report should include the total number of spots found and a markdown summary
    of the best stargazing locations. Do NOT call this tool for clarifying questions or intermediate steps.
    """
    return (
        f"[spots_found={report.spots_found}] "
        f"Report recorded. Now present the following summary to the user:\n\n"
        f"{report.summary}"
    )


#agent for wetaher esolving: it will call Weather services for given locations and will return report for each spot.  

agent_weather_resolver = Agent(
    model=LAZY_STELLAR_MODEL,
    defer_model_check=True,
    capabilities=[WeatherCapability()]
)

@agent.tool
async def check_weather(ctx: RunContext[None], locations: list[str], time_window: str) -> str:
    r = await agent_weather_resolver.run(
        ctx,
        locations=locations,
        time_window=time_window
    return r



@agent_weather_resolver.system_prompt
def get_weather_resolver_system_prompt() -> str:
    return (
        "You are a helpful assistant that checks the weather conditions for stargazing spots. "
        "When given a location and time window, your task is to determine if the weather will be suitable for stargazing. "
        "You should return a structured report indicating whether the weather is good or bad for stargazing, along with any relevant details."
    )   
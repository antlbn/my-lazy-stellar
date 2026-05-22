import os

from pydantic import BaseModel
from pydantic_ai import Agent

from capabilities.search import SearchCapability
from capabilities.weather import WeatherCapability


class AssistantResponse(BaseModel):
    message: str
    spots_found: int
    clarification_needed: bool


# We leave the provider configurable. Defaults to gemini-3-flash-preview.
# Wait, actually let's use a standard fast model.
agent = Agent(
    model="google:gemini-3-flash-preview",
    output_type=AssistantResponse,
    capabilities=[
        SearchCapability(),
        WeatherCapability(),
    ],
)

prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "main_agent.md")
try:
    with open(prompt_path, encoding="utf-8") as f:
        system_prompt = f.read()
except FileNotFoundError:
    system_prompt = "You are Lazy Stellar, a stargazing assistant."


@agent.system_prompt
def get_system_prompt() -> str:
    return system_prompt

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.domain.models import Recommendation
from app.domain.policies import enough_context_to_search, rank_spots
from app.orchestration.state import AstroState
from app.ports.llm_provider import LLMProvider
from app.ports.search_provider import SearchProvider
from app.ports.weather_provider import WeatherProvider

logger = logging.getLogger(__name__)


def make_clarify_node(
    llm: LLMProvider,
) -> Callable[[AstroState], AstroState | dict[str, Any]]:
    """Creates the node that decides whether to ask for more info or proceed to search."""

    prompt_path = Path(__file__).parent.parent / "prompts" / "main_agent.md"
    sys_prompt = (
        prompt_path.read_text(encoding="utf-8")
        if prompt_path.exists()
        else "Ask for location."
    )

    def clarify_node(state: AstroState) -> AstroState | dict[str, Any]:
        ctx = state["context"]
        if enough_context_to_search(ctx):
            return state  # pass through to search

        sys_msg = {"role": "system", "content": sys_prompt}
        msgs = [sys_msg] + state["messages"]
        reply = llm.chat(msgs)
        return {"messages": [{"role": "assistant", "content": reply}]}

    return clarify_node


def make_search_node(
    search: SearchProvider,
) -> Callable[[AstroState], dict[str, Any]]:
    """Creates the node that searches for stargazing spots."""

    def search_node(state: AstroState) -> dict[str, Any]:
        ctx = state["context"]
        query = f"Stargazing spots near {ctx.location}"

        try:
            spots = search.find_spots(query, ctx)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            spots = []

        return {"spots": spots}

    return search_node


def make_weather_node(
    weather: WeatherProvider,
) -> Callable[[AstroState], dict[str, Any]]:
    """Creates the node that fetches weather for the candidate spots."""

    def weather_node(state: AstroState) -> dict[str, Any]:
        recs = []
        for spot in state.get("spots", []):
            try:
                report = weather.get_astro_weather(spot.latitude, spot.longitude)
            except Exception as e:
                logger.error(f"Weather failed for {spot.name}: {e}")
                report = None
            recs.append(Recommendation(spot=spot, weather=report))
        return {"recommendations": recs}

    return weather_node


def make_rank_node(llm: LLMProvider) -> Callable[[AstroState], dict[str, Any]]:
    """Creates the node that ranks the recommendations."""

    def rank_node(state: AstroState) -> dict[str, Any]:
        recs = state.get("recommendations", [])
        ranked = rank_spots(recs)
        # LLM based scoring could happen here, but domain heuristic is used for MVP
        return {"recommendations": ranked[:3]}

    return rank_node


def make_respond_node(
    llm: LLMProvider,
) -> Callable[[AstroState], dict[str, Any]]:
    """Creates the node that formats the final answer to the user."""

    prompt_path = Path(__file__).parent.parent / "prompts" / "main_agent.md"
    sys_prompt = (
        prompt_path.read_text(encoding="utf-8")
        if prompt_path.exists()
        else "Summarize the spots."
    )

    def respond_node(state: AstroState) -> dict[str, Any]:
        recs = state.get("recommendations", [])
        if not recs:
            reply = "I couldn't find any suitable stargazing spots matching your criteria right now."
            return {
                "messages": [{"role": "assistant", "content": reply}],
                "final_answer": reply,
            }

        prompt = (
            "Here are the best stargazing spots we found based on your context:\n\n"
        )
        for i, r in enumerate(recs, 1):
            prompt += f"{i}. {r.spot.name} ({r.spot.latitude}, {r.spot.longitude})\n"
            prompt += f"   Source: {r.spot.source}\n"
            prompt += f"   Description: {r.spot.description}\n"
            if r.weather:
                prompt += f"   Weather: Cloud cover {r.weather.cloud_cover}/9, Transparency {r.weather.transparency}/7.\n"
            else:
                prompt += "   Weather data unavailable.\n"
            prompt += "\n"

        prompt += "Please format this nicely for the user, mentioning the trade-offs and highlighting the weather conditions."

        sys_msg = {"role": "system", "content": sys_prompt}
        msgs = [sys_msg, {"role": "user", "content": prompt}]
        reply = llm.chat(msgs)
        return {
            "messages": [{"role": "assistant", "content": reply}],
            "final_answer": reply,
        }

    return respond_node

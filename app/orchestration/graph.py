from typing import Any

from langgraph.graph import END, START, StateGraph

from app.domain.policies import enough_context_to_search
from app.orchestration.nodes import (
    make_clarify_node,
    make_rank_node,
    make_respond_node,
    make_search_node,
    make_weather_node,
)
from app.orchestration.state import AstroState
from app.ports.llm_provider import LLMProvider
from app.ports.search_provider import SearchProvider
from app.ports.weather_provider import WeatherProvider


def route_after_clarify(state: AstroState) -> str:
    """Determine whether to ask the user a question or proceed to search."""
    if enough_context_to_search(state["context"]):
        return "search"
    return END


def build_graph(
    search: SearchProvider, weather: WeatherProvider, llm: LLMProvider
) -> Any:
    """Build and compile the LangGraph orchestrator."""
    graph = StateGraph(AstroState)

    # Add nodes
    graph.add_node("clarify", make_clarify_node(llm))
    graph.add_node("search", make_search_node(search))
    graph.add_node("weather", make_weather_node(weather))
    graph.add_node("rank", make_rank_node(llm))
    graph.add_node("respond", make_respond_node(llm))

    # Add edges
    graph.add_edge(START, "clarify")

    # Conditional edge: if we have enough context, go to search, else end (wait for user)
    graph.add_conditional_edges(
        "clarify", route_after_clarify, {"search": "search", END: END}
    )

    # Linear flow after search starts
    graph.add_edge("search", "weather")
    graph.add_edge("weather", "rank")
    graph.add_edge("rank", "respond")
    graph.add_edge("respond", END)

    # Compile without internal checkpointing to rely purely on our SessionStore port
    return graph.compile()

from app.domain.models import UserContext
from app.infrastructure.search.fake_search import FakeSearchProvider
from app.infrastructure.weather.fake_weather import FakeWeatherProvider
from app.orchestration.graph import build_graph
from app.orchestration.state import AstroState
from app.ports.llm_provider import LLMProvider


class MockLLM(LLMProvider):
    def chat(self, messages: list[dict[str, str]]) -> str:
        return "Mocked Answer"


def test_graph_flow_with_location() -> None:
    search = FakeSearchProvider()
    weather = FakeWeatherProvider()
    llm = MockLLM()

    orchestrator = build_graph(search, weather, llm)

    state_input: AstroState = {
        "session_id": "test",
        "messages": [],
        "context": UserContext(location="Vienna"),
        "spots": [],
        "recommendations": [],
        "final_answer": "",
    }

    # Because location is provided, the graph should route clarify -> search -> weather -> rank -> respond
    final_state = orchestrator.invoke(state_input)

    assert len(final_state["spots"]) == 2
    assert len(final_state["recommendations"]) == 2
    assert final_state["final_answer"] == "Mocked Answer"
    assert final_state["messages"][-1]["content"] == "Mocked Answer"

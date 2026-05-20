from app.application.chat_use_case import ChatUseCase
from app.infrastructure.search.fake_search import FakeSearchProvider
from app.infrastructure.session.in_memory_store import InMemorySessionStore
from app.infrastructure.weather.fake_weather import FakeWeatherProvider
from app.orchestration.graph import build_graph
from app.ports.llm_provider import LLMProvider


class FakeLLMProvider(LLMProvider):
    def chat(self, messages: list[dict[str, str]]) -> str:
        return "Fake final response based on spots."


def test_chat_use_case_full_flow() -> None:
    search = FakeSearchProvider()
    weather = FakeWeatherProvider()
    llm = FakeLLMProvider()

    orchestrator = build_graph(search, weather, llm)
    session_store = InMemorySessionStore()

    use_case = ChatUseCase(orchestrator, session_store)

    # Send a message containing a location
    response = use_case.handle_message("test-session-123", "Paris")

    assert "Fake final response" in response.text
    session = session_store.load("test-session-123")
    assert session is not None
    assert session.state["context"].location == "Paris"

    # Ensure our fake search provider returned the expected spots
    assert len(session.state["spots"]) == 2
    assert session.state["spots"][0].name == "Fake Park 1"

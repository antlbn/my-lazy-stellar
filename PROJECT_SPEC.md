# Lazy Stellar Project Specification

## Goal

Lazy Stellar is a provider-agnostic conversational recommender for stargazing.

The user interacts with a chat agent. The agent keeps session context, asks clarifying questions, searches the internet for realistic stargazing options, checks astronomy-oriented weather, and returns a short list of recommendations with sources and reasoning.

The MVP is intentionally small. It is not yet a shared location database or a long-term knowledge platform. Found locations, ratings, and trade-offs live mostly inside the chat session.

## Product Scenario

The core scenario:

1. The user asks where they can observe stars.
2. The assistant asks for missing constraints when needed: location, travel radius, transport, telescope availability, safety concerns, time window.
3. A search agent finds candidate spots, observatories, events, or amateur astronomy meetups.
4. A weather agent checks cloud cover, transparency, seeing, wind, and temperature.
5. The main agent compares the options and returns 1-3 best recommendations.
6. The user can ask follow-up questions in the same session.

## Architectural Principle

The agent runtime is not the center of the architecture.

PydanticAI, PydanticGraph, model providers, weather APIs, search APIs, databases, and UI frameworks are infrastructure choices. The application should depend on narrow interfaces and adapters, not on a single framework everywhere.

The current target is:

```text
┌─────────────────────────────────────┐
│              Domain                 │
│  Pure Python / pure Pydantic models  │
│  Agent policy / tools / prompts      │
└────────────────┬────────────────────┘
                 │ called by
┌────────────────▼────────────────────┐
│        Orchestration Layer           │
│  PydanticGraph / typed nodes         │
│  Framework code is isolated here      │
└────────────────┬────────────────────┘
                 │ calls through ports
┌────────────────▼────────────────────┐
│          Adapter Layer               │
│  LLM / search / weather / session DB  │
│  Provider-specific implementations    │
└─────────────────────────────────────┘
```

PydanticAI and PydanticGraph are the primary orchestration tools:

- PydanticGraph for explicit orchestration, state transitions, and type-safe agent flow.
- PydanticAI `Agent` instances inside nodes for strictly typed LLM interactions.
- No direct framework dependency inside domain policies, provider contracts, or presentation code.

## Business Logic

Business logic is the set of product rules that turn a vague user request into useful recommendations.

For this project, business logic includes:

- deciding whether the agent has enough context to search;
- asking useful clarifying questions;
- choosing what kind of places to search for;
- interpreting search results as candidate stargazing options;
- interpreting astronomy weather for observation quality;
- balancing sky quality, accessibility, safety, event relevance, and weather;
- explaining trade-offs in a concise chat answer;
- preserving relevant session context for follow-up questions.

The business logic is split between code, prompt policy, and evals.

## Prompt Policy

Prompts are not the business core by themselves.

A prompt is a model-executed specification of expected behavior. It is the agent's attempt to follow business logic, not a guaranteed rule engine.

Prompts should describe:

- the role of the main assistant;
- when to ask clarifying questions;
- how search and weather agents should be used;
- how to rank options in natural language;
- how to explain uncertainty;
- the expected answer format.

Code should enforce or support:

- provider interfaces;
- session persistence;
- fallback behavior;
- response schemas where useful;
- error handling;
- deterministic normalization of external API responses;
- trace collection for tests and debugging.

Evals should verify:

- final answer quality;
- session memory behavior;
- tool and subagent call order;
- presence of sources, coordinates, and weather interpretation;
- whether user constraints were actually respected.

## Recommended Patterns

Use these patterns pragmatically.

### Ports and Adapters

External systems should be behind local interfaces:

- `LLMProvider`
- `SearchProvider`
- `WeatherProvider`
- `SessionStore`
- `TraceRecorder`
- `ChatView`

Concrete implementations can use Gemini, OpenAI, Anthropic, Tavily, Google Search, 7timer, Open-Meteo, SQLite, Postgres, local memory, ADK, or LangGraph.

### Application Service / Use Case

The chat scenario should have a clear entrypoint:

```text
ChatUseCase.handle_message(session_id, user_message) -> AssistantResponse
```

This use case owns the application flow:

- load session;
- call orchestration layer;
- save resulting state;
- return a response model for presentation.

### Orchestrator

The orchestrator coordinates the agent workflow.

With PydanticGraph, this is the only layer that should know about:

- `pydantic_graph.Graph` and `Node`;
- strict Pydantic state schemas;
- PydanticAI `Agent` injections;
- conditional routing via typed returns.

### Humble Object / Presenter

The UI should stay simple.

Presentation code should convert application responses into view models. It should not know which LLM, graph, weather API, or search provider is used.

### Strategy / Fallback Provider

Weather and search providers should be swappable.

Example:

```text
FallbackWeatherProvider
  -> SevenTimerWeatherProvider
  -> OpenMeteoWeatherProvider
  -> StaticWeatherProvider for tests
```

### Dependency Inversion

The application depends on interfaces. Infrastructure implements them.

This keeps the project provider-agnostic and prevents PydanticAI or any other framework from leaking into every layer.

## Suggested Runtime Flow

```text
User
  -> UI / API / CLI
  -> Presenter
  -> ChatUseCase
  -> PydanticGraphOrchestrator
  -> MainAgentNode
  -> SearchNode when needed
  -> WeatherNode when coordinates exist
  -> RankingNode or main agent ranking step
  -> FinalAnswerNode
  -> Presenter
  -> User
```

For the MVP, ranking may remain LLM-based in the prompt policy. Later, if recommendations become persistent or more critical, ranking can be moved into deterministic domain code.

## Suggested File Structure

```text
app/
  __init__.py
  config.py

  domain/
    __init__.py
    models.py
    policies.py

  application/
    __init__.py
    chat_use_case.py
    responses.py

  prompts/
    main_agent.md
    search_agent.md
    weather_agent.md
    ranking_policy.md

  ports/
    __init__.py
    llm_provider.py
    search_provider.py
    weather_provider.py
    session_store.py
    trace_recorder.py

  orchestration/
    __init__.py
    state.py
    nodes.py
    graph.py

  infrastructure/
    __init__.py
    llm/
      langchain_chat_model.py
      gemini_provider.py
      openai_provider.py
    search/
      google_search_provider.py
      fake_search_provider.py
    weather/
      seven_timer_provider.py
      open_meteo_provider.py
      fallback_weather_provider.py
      fake_weather_provider.py
    session/
      in_memory_session_store.py
      sqlite_session_store.py

  presentation/
    __init__.py
    presenter.py
    view_models.py

  entrypoints/
    cli.py
    local_api.py
    agent_engine_app.py

frontend/
  index.html

evals/
  promptfoo.yaml
  cases/
    vienna_no_car.yaml
    paris_followup.yaml

tests/
  unit/
    test_weather_normalization.py
    test_fallback_weather_provider.py
    test_presenter.py
  integration/
    test_chat_use_case_with_fakes.py
    test_langgraph_trace.py

scripts/
  smoke_local.sh
  deploy_dev.sh
```

This structure is a target, not a requirement to create everything at once.

## Testing Strategy

Use three complementary layers.

### Unit Tests

Use for deterministic code:

- weather response normalization;
- fallback provider behavior;
- presenter formatting;
- session store behavior;
- simple policy helpers.

### Trace-Aware Integration Tests

Use Python tests for orchestration behavior:

- search node was called before weather node;
- weather was called only after coordinates were available;
- fallback provider was used when primary provider failed;
- session context was preserved between turns.

Promptfoo is not ideal for this because it is mostly black-box and does not naturally inspect graph traces or subagent calls.

### Black-Box Evals

Use promptfoo or similar tools for final answer quality:

- answer contains 1-3 realistic recommendations;
- answer includes sources and coordinates;
- answer accounts for transport constraints;
- answer explains weather risks;
- follow-up questions use previous context.

## Dependency Rule

Allowed dependencies:

```text
presentation -> application -> orchestration -> ports
infrastructure -> ports
orchestration -> ports
domain -> no framework dependencies
```

Forbidden dependencies:

```text
domain -> pydantic_ai (only pure pydantic is allowed)
domain -> pydantic_graph
domain -> provider SDKs
application -> concrete weather/search providers
presentation -> agent runtime
```

## MVP Refactor Plan

Start small:

1. Move prompts out of `app/agent.py`.
2. Add ports for weather, search, LLM, and session memory.
3. Move 7timer access into `SevenTimerWeatherProvider`.
4. Add fake weather/search providers for tests.
5. Add a `ChatUseCase`.
6. Introduce PydanticGraph only inside `app/orchestration`.
7. Add trace-aware pytest tests.
8. Add promptfoo evals for answer quality.
9. Keep local run simple through `uv` and `make`.

The goal is not to hide that PydanticAI is used. The goal is to prevent the whole application from becoming deeply coupled to any specific framework.

## Future Roadmap (Post-MVP)

1. **Agnostic Interfaces**: Implement multiple frontend entrypoints (e.g., Telegram Bot, CLI, Web UI) reusing the same `ChatUseCase` without modifying business logic.
2. **Observability & Evaluation**: Expand tracing capabilities (e.g., via LangSmith or OpenTelemetry) to monitor token usage, latency, and agent decision-paths, ensuring production readiness.
3. **Persistent Location Knowledge Base**: Introduce a database table for stargazing spots and astronomical events. Agents can query this database as a primary source and actively populate it from search results.
4. **Extensible Multi-Agent System**: Expand the pool of sub-agents (e.g., adding an "Evaluator/Critic" agent to double-check recommendations before returning them).

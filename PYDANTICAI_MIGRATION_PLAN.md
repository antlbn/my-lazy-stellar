# План реализации на PydanticAI

Этот документ описывает порядок имплементации целевой архитектуры MVP.
Он дополняет `ARCHITECTURE.md` и `decisions.md`, но не заменяет их.

## Цель реализации

Построить целевую реализацию на PydanticAI, используя существующие наброски только там, где они совпадают с архитектурой.

- `domain` не знает про PydanticAI;
- `application` вызывает orchestration через простой контракт;
- `orchestration` содержит PydanticAI Agent, tools и structured output;
- `infrastructure` реализует внешние providers;
- tests продолжают использовать fake providers.

Существующий LangGraph/LangChain код считается черновиком. Его не нужно беречь, если прямое удаление или замена делает архитектуру проще и чище.

## MVP scope

В первой реализации делаем только:

- сбор пользовательских ограничений;
- поиск 3-5 подходящих мест;
- проверку погоды;
- LLM ranking и объяснение;
- persistent sessions;
- tracing через Logfire.

Не делаем в первом проходе:

- sky calendar;
- astro events;
- nature conditions;
- critic agent;
- Pydantic Graph.

## Шаг 0. Зафиксировать текущую точку входа

Файлы:

- `app/application/chat_use_case.py`
- `entrypoints/local_api.py`
- `app/application/responses.py`

Решение:

```text
ChatUseCase.handle_message(session_id, text) -> AssistantResponse
```

остается главным контрактом.

Почему:

Если внешний contract не меняется, можно построить новый orchestration runtime без переписывания FastAPI и frontend.

Готово, когда:

- `ChatUseCase` по-прежнему загружает сессию;
- вызывает orchestrator;
- сохраняет сессию;
- возвращает `AssistantResponse`.

## Шаг 1. Добавить зависимости

Файл:

- `pyproject.toml`

Добавить:

```toml
"logfire>=4.33.0"
"pydantic-ai-slim[logfire,openai]>=1.99.0"
```

Не добавлять прямой зависимостью:

```toml
"pydantic-graph"
```

Почему:

Используем `pydantic-ai-slim`, потому что полный `pydantic-ai` подтягивает много provider-интеграций, которые MVP не использует. Extra `openai` нужен для OpenAI/OpenRouter-compatible моделей, `logfire` - для observability.

Pydantic Graph не добавляем как прямую зависимость. Он может появиться транзитивно внутри PydanticAI, но в коде мы не используем graph API, пока один PydanticAI Agent с tools удерживает workflow.

Проверка:

```bash
uv sync
uv run python -c "import pydantic_ai, logfire"
```

## Шаг 2. Добавить output models

Файл:

- `app/application/responses.py`

Добавить Pydantic-модели для structured agent output.

Пример:

```python
from pydantic import BaseModel, Field


class RecommendedSpotOutput(BaseModel):
    name: str
    latitude: float
    longitude: float
    source: str
    description: str
    weather_summary: str
    accessibility: str
    safety_assessment: str
    rank_reason: str


class ChatAgentOutput(BaseModel):
    answer: str
    recommendations: list[RecommendedSpotOutput] = Field(min_length=0, max_length=5)
    assumptions: list[str] = []
    follow_up_question: str | None = None
```

Почему:

Свободный текст плохо тестируется. Structured output позволяет проверять, что агент реально вернул места, причины, погоду и assumptions.

Готово, когда:

- модели импортируются без зависимости от PydanticAI;
- tests могут проверять `recommendations`, а не только текст.

## Шаг 3. Ввести orchestration contract

Новый файл:

- `app/orchestration/pydantic_ai_orchestrator.py`

Добавить простой класс:

```python
class PydanticAIOrchestrator:
    def handle(self, session_id: str, messages: list[dict[str, str]]) -> ChatAgentOutput:
        ...
```

Почему:

`ChatUseCase` не должен напрямую знать про `Agent.run`, `RunContext`, deps, tools или model settings.

Готово, когда:

- `ChatUseCase` может вызвать `.handle(...)`;
- старый LangGraph orchestrator пока остается рядом;
- новая реализация может тестироваться отдельно.

## Шаг 4. Ввести AgentDeps

Файл:

- `app/orchestration/pydantic_ai_orchestrator.py`

Добавить:

```python
from dataclasses import dataclass

from app.ports.search_provider import SearchProvider
from app.ports.weather_provider import WeatherProvider


@dataclass
class AgentDeps:
    search: SearchProvider
    weather: WeatherProvider
```

Почему:

Это способ PydanticAI передать tools доступ к инфраструктуре, не нарушая dependency rules.

Правильная зависимость:

```text
PydanticAI tool -> AgentDeps -> Port -> Adapter
```

Неправильная зависимость:

```text
PydanticAI tool -> DuckDuckGo / 7timer directly
```

## Шаг 5. Создать PydanticAI Agent

Файл:

- `app/orchestration/pydantic_ai_orchestrator.py`

Нужен агент примерно такого типа:

```python
from pydantic_ai import Agent

agent = Agent(
    model=...,
    deps_type=AgentDeps,
    output_type=ChatAgentOutput,
    system_prompt=...,
)
```

Prompt брать из:

- `app/prompts/main_agent.md`

Почему:

PydanticAI Agent становится единственным местом, где LLM принимает решения: уточнять, искать, проверять погоду, ранжировать.

Готово, когда:

- агент возвращает `ChatAgentOutput`;
- prompt не содержит post-MVP требований про sky calendar/nature conditions.

## Шаг 6. Обернуть SearchProvider как tool

Файл:

- `app/orchestration/pydantic_ai_orchestrator.py`

Tool:

```python
@agent.tool
async def search_spots(ctx: RunContext[AgentDeps], query: str, location: str, transport: str | None = None, radius_km: float | None = None) -> list[StargazingSpot]:
    ...
```

Внутри:

- собрать `UserContext`;
- вызвать `ctx.deps.search.find_spots(...)`;
- вернуть нормализованные spots.

Почему:

Агенту нужен tool-level интерфейс. Приложению нужен provider-level интерфейс. Tool является адаптером между ними.

Готово, когда:

- fake search provider работает через этот tool;
- реальный search provider не импортируется в orchestration.

## Шаг 7. Обернуть WeatherProvider как tool

Файл:

- `app/orchestration/pydantic_ai_orchestrator.py`

Tool:

```python
@agent.tool
async def get_astro_weather(ctx: RunContext[AgentDeps], latitude: float, longitude: float) -> WeatherReport:
    ...
```

Почему:

Погода должна быть внешней возможностью агента, но конкретный `7timer` остается за `WeatherProvider`.

Готово, когда:

- fake weather provider работает через tool;
- failures превращаются в понятное для агента сообщение или nullable weather result;
- domain не знает про PydanticAI.

## Шаг 8. Переписать prompt под MVP

Файл:

- `app/prompts/main_agent.md`

Prompt должен сказать агенту:

- если нет локации, спросить локацию;
- если есть только локация, спросить транспорт/радиус/время/safety одним коротким вопросом;
- если пользователь просит быстро, продолжить с assumptions;
- найти 3-5 мест;
- проверить погоду для каждого места;
- ранжировать через LLM;
- вернуть ответ на языке пользователя;
- не обещать sky calendar/astro events/nature conditions в MVP.

Почему:

Архитектура задает границы, prompt задает поведение агента внутри этих границ.

Готово, когда:

- prompt не противоречит `ARCHITECTURE.md`;
- tests могут подтвердить clarification-first UX.

## Шаг 9. Подключить orchestrator в ChatUseCase

Файл:

- `app/application/chat_use_case.py`

Изменение:

- не создавать `UserContext(location=text)` эвристически на первый message;
- передавать историю сообщений в PydanticAI orchestrator;
- сохранять `answer` и structured state.

Почему:

Сейчас код считает первое сообщение локацией. Это ломает clarification-first UX: пользователь может написать “хочу звезды на выходных”, а система решит, что это location.

Готово, когда:

- новая сессия не превращает любой первый текст в `location`;
- agent сам уточняет недостающий контекст;
- старые tests обновлены под новое поведение.

## Шаг 10. Подключить в entrypoint

Файл:

- `entrypoints/local_api.py`

Заменить:

```python
orchestrator = build_graph(...)
```

на:

```python
orchestrator = PydanticAIOrchestrator(...)
```

Почему:

Это точка переключения runtime. FastAPI endpoint не должен измениться.

Готово, когда:

- `POST /chat` работает через PydanticAI;
- frontend не требует изменений.

## Шаг 11. Добавить SQLite SessionStore

Новые/изменяемые файлы:

- `app/infrastructure/session/sqlite_store.py`
- `app/ports/session_store.py`
- `tests/unit/test_sqlite_session_store.py`

Что хранить:

- `session_id`;
- messages;
- structured agent state;
- timestamps.

Почему:

MVP требует, чтобы сессии переживали перезапуск приложения.

Готово, когда:

- после создания нового `SQLiteSessionStore` можно загрузить старую сессию;
- in-memory store остается для тестов.

## Шаг 12. Подключить Logfire

Файлы:

- `entrypoints/local_api.py`
- `app/application/chat_use_case.py`
- `app/orchestration/pydantic_ai_orchestrator.py`
- adapters search/weather

Минимум:

```python
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()
```

Custom spans:

- `chat.request`;
- `session.load`;
- `agent.run`;
- `search.find_spots`;
- `weather.get_astro_weather`;
- `session.save`.

Почему:

Agent-системы сложно отлаживать только логами. Нужен trace, где видно tool calls, latency, failures и model output.

Готово, когда:

- локально приложение работает без Logfire token;
- при наличии token traces уходят в Logfire;
- secrets и полный приватный контекст не пишутся бездумно.

## Шаг 13. Обновить тесты

Файлы:

- `tests/integration/test_chat_use_case_fakes.py`
- `tests/integration/test_graph_trace.py`
- `tests/unit/test_domain_policies.py`
- новые tests для PydanticAI orchestrator.

Изменения:

- `test_graph_trace.py` переименовать или заменить, так как graph больше не основной runtime;
- добавить test, что vague first message вызывает clarification;
- добавить test, что enough context вызывает search/weather;
- добавить test, что output содержит до 5 recommendations;
- добавить test, что fake providers используются без сети.

Почему:

Тесты должны проверять архитектурное поведение, а не конкретную старую реализацию LangGraph.

## Шаг 14. Удалить черновой runtime

Файлы-кандидаты:

- `app/orchestration/graph.py`
- `app/orchestration/nodes.py`
- `app/orchestration/state.py`
- LangChain/LangGraph dependencies в `pyproject.toml`

Делать только после:

- PydanticAI flow работает;
- tests green;
- README обновлен;
- нет импортов старого runtime.

Проверки:

```bash
rg "langgraph|langchain|build_graph|StateGraph"
uv run pytest
uv run ruff check .
```

## Когда добавлять Pydantic Graph

Не добавлять в первом проходе.

Добавить, если появится одно из условий:

- агент неустойчиво соблюдает порядок steps;
- weather checks нужно гарантированно выполнять параллельно;
- нужен resumable workflow;
- нужны typed transitions и явное состояние между шагами;
- tests должны проверять путь выполнения, а не только результат;
- orchestration logic стала слишком сложной для одного Agent.

Тогда graph должен жить только в `app/orchestration`.

## Рекомендуемый порядок коммитов

1. Add PydanticAI and Logfire dependencies.
2. Add structured output models.
3. Add PydanticAI orchestrator skeleton.
4. Add AgentDeps and tools over SearchProvider/WeatherProvider.
5. Switch ChatUseCase and local API to PydanticAI.
6. Rewrite MVP prompt.
7. Update fake-provider integration tests.
8. Add SQLite session store.
9. Add Logfire instrumentation.
10. Remove LangGraph/LangChain runtime.

## Главный риск

Главный риск реализации - смешать framework code с domain/application.

Если при реализации появляется желание импортировать PydanticAI в `app/domain` или конкретный provider в `app/application`, это сигнал остановиться и добавить/поправить port.

# Архитектура Lazy Stellar

## Статус

Этот файл является основным источником правды по архитектуре MVP.
`PROJECT_SPEC.md` и старые заметки считаются историческим контекстом, если они противоречат этому документу.

Текущий код еще не полностью соответствует целевой архитектуре: часть реализации использует LangGraph/LangChain. Целевое решение для MVP - PydanticAI, с возможным добавлением Pydantic Graph, если одного PydanticAI станет недостаточно для явной оркестрации.

## Цель MVP

Lazy Stellar - чат-ассистент для поиска доступных мест для наблюдения звезд.

MVP должен:

- распрашивать пользователя о недостающих ограничениях;
- искать 3-5 доступных мест рядом с заданной локацией;
- проверять astronomy-oriented weather для найденных мест;
- выдавать ранжированную рекомендацию с кратким объяснением trade-offs;
- сохранять сессии между перезапусками приложения, чтобы к ним можно было вернуться.

Не входит в MVP:

- общая база мест для всех пользователей;
- социальные отзывы и рейтинги;
- полноценная карта и навигация;
- сложная deterministic ranking engine;
- проверка текущих астрономических событий и видимых объектов;
- уточнение состояния природы и сезонных факторов: насекомые, снег, закрытые тропы, wildlife, влажность, локальные ограничения.

## Архитектурный принцип

Фреймворк агента не должен стать центром всей системы.

PydanticAI, Pydantic Graph, поисковые API, weather API, календарные источники, база данных и UI являются инфраструктурными решениями. Основной код должен зависеть от узких локальных интерфейсов.

```text
Presentation / EntryPoints
  -> Application
  -> Orchestration
  -> Ports
  -> Infrastructure Adapters

Domain
  -> no framework dependencies
```

## Слои

### Domain

Содержит чистые модели и правила предметной области.

Примеры:

- `UserContext`
- `StargazingSpot`
- `WeatherReport`
- `Recommendation`
- политики достаточности контекста;
- простые threshold-правила для погоды;
- будущие deterministic ranking helpers.

Domain не должен импортировать PydanticAI, Pydantic Graph, FastAPI, SDK провайдеров, search/weather clients.

### Application

Содержит use case уровня продукта.

Основной контракт:

```text
ChatUseCase.handle_message(session_id, user_message) -> AssistantResponse
```

Use case:

- загружает сессию;
- передает сообщение в оркестратор;
- сохраняет обновленную сессию;
- возвращает ответ для presentation layer.

Application не должен знать конкретные реализации LLM, search, weather или storage.

### Orchestration

Координирует агентный сценарий.

Целевое решение:

- PydanticAI Agent как основной runtime для LLM reasoning, tools и structured output;
- Pydantic Graph только если понадобится явный typed workflow, ветвления, parallel steps или traceable graph state.

Базовый flow:

```text
User message
  -> Load session
  -> Main Agent
  -> Clarify if context is incomplete
  -> Search spots
  -> Check astronomy weather
  -> LLM ranking and explanation
  -> Save session
  -> Return answer
```

Для MVP ранжирование остается на стороне LLM. Код может помогать нормализацией данных и простыми safety/weather flags. Если качество ранжирования станет нестабильным, scoring переносится в domain/application code.

### Ports

Ports задают границы внешних возможностей:

- `LLMProvider`
- `SearchProvider`
- `WeatherProvider`
- `SessionStore`
- `TraceRecorder`

Даже если PydanticAI дает готовый инструмент поиска, приложение должно использовать локальный порт. Это оставляет возможность заменить встроенный `WebSearchTool`, DuckDuckGo, Tavily, Exa, Google Search или MCP tool без переписывания use case.

### Infrastructure

Infrastructure реализует ports:

- PydanticAI/OpenRouter/Gemini/OpenAI adapter для LLM;
- search adapter через PydanticAI web search tools, DuckDuckGo, Tavily, Exa или другой provider;
- `7timer` adapter для astronomy weather;
- fake providers для тестов;
- persistent session store.

## Поиск

Целевое решение - `SearchProvider` как граница приложения.

Внутри search adapter можно использовать:

- PydanticAI `WebSearchTool`, если выбранный model/provider поддерживает native web search;
- PydanticAI common tools: DuckDuckGo, Tavily, Exa;
- LangChain tool через PydanticAI integration как временный мост;
- MCP search tool, если появится отдельный search server.

Причина: выбор поисковика является инфраструктурной деталью, а не бизнес-правилом.

## Погода

MVP использует один реальный weather provider: `7timer` astronomy API.

Для тестов используется fake weather provider.

Fallback между несколькими weather providers не является обязательным для MVP. Если он появится, его место - infrastructure/application boundary:

```text
WeatherProvider port
  <- FallbackWeatherProvider
       -> SevenTimerWeatherProvider
       -> SecondaryWeatherProvider
       -> StaticWeatherProvider for tests
```

PydanticAI `FallbackModel` подходит для fallback между LLM-моделями и model/native-tool failures. Для weather/search API лучше держать fallback в adapter layer, чтобы orchestration и domain видели один стабильный порт.

## Расширения после MVP

После MVP система может быть расширена отдельными возможностями:

- `SkyCalendarProvider` для проверки текущих астрономических событий и видимых объектов;
- `NatureConditionsProvider` для сезонных и природных факторов: снег, закрытые тропы, насекомые, wildlife, влажность, локальные ограничения;
- critic/evaluator agent для финальной проверки рекомендаций.

Эти возможности не должны быть спрятаны только в prompt. Когда они появятся, их нужно оформлять как отдельные ports/adapters, чтобы их можно было тестировать и заменять.

## Сессии

Сессии должны жить между включением и выключением приложения.

MVP-решение: persistent `SessionStore`, предпочтительно SQLite.

Причины:

- минимальная операционная сложность;
- легко запускать локально;
- достаточно для возврата к старым чатам;
- можно заменить на Postgres без изменения `ChatUseCase`.

In-memory store допустим только для тестов и временной локальной разработки.

## Tracing и Observability

MVP использует Pydantic Logfire как основную систему observability.

Причины:

- PydanticAI имеет нативную интеграцию с Logfire;
- Logfire построен на OpenTelemetry, поэтому данные можно отправить в другой OTel-compatible backend;
- для агентного приложения важен full-stack trace: HTTP request, session load/save, agent run, LLM calls, tool calls, search/weather calls;
- Logfire поддерживает AI-specific visibility: token/cost tracking, tool call inspection, multi-turn conversations и eval traces.

Минимальный набор spans:

- `chat.request`;
- `session.load`;
- `agent.run`;
- `search.find_spots`;
- `weather.get_astro_weather`;
- `ranking.generate`;
- `session.save`.

Правило границы: observability instrumentation не должна попадать в domain layer.

Допустимые места instrumentation:

- entrypoints/presentation для HTTP spans;
- application layer для use-case spans;
- orchestration layer для agent/tool spans;
- infrastructure adapters для внешних API spans.

Sensitive data policy:

- не писать secrets/API keys в traces;
- осторожно относиться к полному user prompt/history;
- для MVP можно логировать session_id, provider name, latency, status, counts, но не приватные данные пользователя без явной необходимости.

## Уточняющие вопросы

Минимально обязательный контекст для старта сценария - локация.

Но если пользователь дал только локацию, ассистент должен задать короткий уточняющий вопрос перед поиском, чтобы получить хотя бы основные ограничения:

- транспорт;
- радиус поездки;
- временное окно;
- safety/accessibility concerns;
- телескоп или наблюдение невооруженным глазом.

Если пользователь явно просит "без уточнений", "любой вариант", "быстро", ассистент может продолжить с разумными defaults и явно указать предположения.

## Ответ пользователю

Финальный ответ должен содержать:

- 3-5 найденных мест, если данных достаточно;
- ранжирование или явный top pick;
- краткие причины выбора;
- weather summary;
- accessibility/safety notes;
- источники или provenance, когда доступны;
- вопрос для следующего шага, если нужен выбор времени, транспорта или направления.

## Dependency Rules

Разрешено:

```text
presentation -> application
application -> domain
application -> ports
application -> orchestration
orchestration -> domain
orchestration -> ports
infrastructure -> ports
infrastructure -> domain models
```

Запрещено:

```text
domain -> pydantic_ai
domain -> pydantic_graph
domain -> langchain
domain -> provider SDKs
application -> concrete provider adapters
presentation -> agent runtime
ports -> infrastructure
```

## Тестирование

MVP должен иметь три уровня проверок:

- unit tests для domain policies, weather normalization, session store;
- integration tests с fake providers для полного chat flow;
- evals для качества финального ответа: 3-5 мест, соблюдение ограничений, погода, объяснение trade-offs.

## Известные расхождения с текущим кодом

- Код сейчас использует LangGraph/LangChain, а целевая архитектура - PydanticAI и возможно Pydantic Graph.
- Сессии сейчас in-memory, а MVP требует persistent session store.
- Ранжирование в коде частично deterministic, но целевое MVP-решение - LLM ranking с возможным переносом scoring в код позже.
- Старый README описывает Google ADK; это не целевое решение.

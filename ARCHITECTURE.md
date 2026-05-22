# Архитектура Lazy Stellar

## Статус

Главный источник правды по архитектуре MVP.

---

## Цель MVP

Lazy Stellar — чат-ассистент для поиска мест наблюдения звёздного неба.

MVP должен:

- уточнять у пользователя недостающие ограничения;
- находить 3–5 доступных мест рядом с заданной локацией;
- проверять astronomy weather для найденных мест;
- выдавать ранжированную рекомендацию с кратким объяснением trade-offs;
- сохранять сессии между перезапусками приложения.

Не входит в MVP:

- общая база мест для всех пользователей;
- социальные отзывы и рейтинги;
- полноценная карта и навигация;
- проверка астрономических событий и видимых объектов;
- сезонные факторы: насекомые, снег, закрытые тропы, wildlife.

---

## Архитектурный подход

**PydanticAI-native**: используем фреймворк в том виде, в котором он задуман —
`Agent`, `Capability`, `Hooks`, `deps_type`. Без слоёв ради слоёв.

Фреймворк не защищает от плохих решений автоматически.
Три правила, которые нужно держать руками:

### Правило 1 — Бизнес-логика не живёт в tools

Tool — мост между агентом и внешним миром.
Правила («считается ли погода хорошей», «достаточно ли данных для поиска») —
отдельные чистые функции в `core/`, без I/O, без `pydantic_ai`.

### Правило 2 — Зависимости инжектируются, не хардкодятся

Capability-классы принимают реализации снаружи (через конструктор).
Это позволяет подменять их в тестах без портов и адаптеров:

```python
class SearchCapability(Capability):
    def __init__(self, search_fn=None):
        self._search = search_fn or duckduckgo_search  # инъекция
```

### Правило 3 — `core/` не импортирует фреймворк

Модели данных и политики — чистый Python.
Нарушение: любой `import pydantic_ai` в `core/`.

---

## Структура проекта

```text
lazy_stellar/
  core/
    models.py          # StargazingSpot, WeatherReport, UserContext — dataclasses
    policies.py        # weather_ok(), enough_context(), rank_spots() — pure functions
  capabilities/
    search.py          # SearchCapability — tool find_spots()
    weather.py         # WeatherCapability — tool get_astro_weather()
  storage/
    session.py         # SQLite session read/write
  agent.py             # Agent + Capabilities + system prompt
  prompts/
    main_agent.md      # system prompt
entrypoints/
  cli.py / api.py
```

---

## Flow

```text
User message
  -> Load session (SQLite)
  -> Agent.run() с history
  -> [Clarify] если нет локации или базовых ограничений
  -> [search_spots] tool
  -> [get_astro_weather] tool для каждого места
  -> LLM ранжирует и объясняет trade-offs
  -> Save session
  -> Return answer
```

---

## Агент

Один `Agent` с двумя Capability:

- `SearchCapability` — инжектирует `search_fn`; внутри — DuckDuckGo / Tavily / Exa
- `WeatherCapability` — инжектирует `weather_fn`; внутри — 7timer astronomy API

`deps_type` — dataclass с инжектированными callable:

```python
@dataclass
class Deps:
    search_fn: SearchFn
    weather_fn: WeatherFn
```

Ранжирование для MVP — на стороне LLM.
Если качество станет нестабильным — scoring переносится в `core/policies.py`.

---

## Сессии

SQLite. Хранит `(session_id, history_json, updated_at)`.
In-memory — только для тестов.

---

## Observability

Logfire как основная система tracing.

```python
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)
```

Минимальный набор spans: `chat.request`, `agent.run`, `search.find_spots`,
`weather.get_astro_weather`, `session.load`, `session.save`.

Sensitive data: не писать API keys и полный user input в traces без явной необходимости.

---

## Уточняющие вопросы

Минимум для старта сценария — локация.

Если дана только локация, агент задаёт короткий уточняющий вопрос:

- транспорт и радиус поездки;
- временное окно;
- safety / accessibility;
- телескоп или невооружённым глазом.

Если пользователь просит «без уточнений» — агент продолжает с разумными defaults
и явно указывает предположения.

---

## Финальный ответ

- 3–5 мест;
- явный top pick или ранжирование;
- краткие причины выбора;
- weather summary;
- accessibility / safety notes;
- источники, если доступны;
- вопрос для следующего шага, если нужен.

---

## Тестирование

- **Unit**: функции `core/policies.py` — без моков, без фреймворка.
- **Integration**: `Agent` с `TestModel` + fake `search_fn` / `weather_fn` через инъекцию.
- **Evals**: качество финального ответа — 3–5 мест, соблюдение ограничений, погода, trade-offs.

---

## После MVP

Отдельные расширения, когда понадобятся:

- `SkyCalendarCapability` — текущие астрономические события;
- `NatureConditionsCapability` — сезонные факторы;
- critic/evaluator agent для финальной проверки рекомендаций.

Каждое расширение — отдельный Capability с инжектируемой реализацией.

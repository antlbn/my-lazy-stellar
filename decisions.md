# Архитектурные решения

Этот файл фиксирует решения MVP. Формат намеренно проще ADR: номер, статус, решение, причина, последствия.

## D001. PydanticAI как целевой agent runtime

Статус: принято.

Решение: использовать PydanticAI как основной фреймворк для агентной логики MVP.

Причина: PydanticAI дает agent abstraction, typed output, tools/toolsets, model providers, testing patterns и интеграции, не заставляя писать весь workflow на низком уровне.

Последствия:

- текущий LangGraph/LangChain код должен рассматриваться как переходная реализация;
- PydanticAI не должен протекать в domain layer;
- orchestration layer может знать о PydanticAI.

## D002. Pydantic Graph только при необходимости

Статус: принято.

Решение: не добавлять Pydantic Graph заранее. Использовать его, если PydanticAI Agent станет недостаточно для явного workflow.

Причина: MVP-flow пока можно описать как один агент с tools и structured context. Graph нужен, если появятся сложные ветвления, parallel calls, joins, reducers или требования к traceable typed state.

Последствия:

- сначала проектируется чистая граница orchestration;
- замена внутреннего orchestration runtime не должна менять application/domain contracts.

## D003. Ports остаются обязательной границей

Статус: принято.

Решение: внешние возможности доступны через ports: `LLMProvider`, `SearchProvider`, `WeatherProvider`, `SessionStore`.

Причина: даже если PydanticAI предоставляет готовые tools, выбор поисковика и weather API остается инфраструктурной деталью.

Последствия:

- use case не зависит от конкретного search/weather SDK;
- fake providers остаются простыми;
- можно заменить DuckDuckGo/Tavily/Exa/Google/MCP без переписывания сценария.

## D004. SearchProvider поверх PydanticAI search capabilities

Статус: принято.

Решение: использовать локальный `SearchProvider` как контракт, а внутри adapter можно подключать PydanticAI web search tools, common tools, LangChain bridge или MCP.

Причина: PydanticAI поддерживает несколько способов поиска: built-in web search для поддерживаемых model providers, common tools вроде DuckDuckGo/Tavily/Exa, third-party LangChain tools и MCP toolsets. Это полезно, но не должно становиться публичным контрактом приложения.

Последствия:

- search adapter может меняться без изменения domain/application;
- результаты поиска нужно нормализовать в `StargazingSpot`;
- parsing/validation search results должны быть тестируемыми.

## D005. Weather fallback живет за WeatherProvider

Статус: принято.

Решение: MVP использует один реальный weather provider (`7timer`) и fake provider для тестов. Если появится fallback, он реализуется как adapter за `WeatherProvider`.

Причина: PydanticAI `FallbackModel` решает fallback между LLM-моделями и model/native-tool failures. Fallback внешних weather/search APIs лучше держать в инфраструктурном adapter, чтобы приложение видело один стабильный contract.

Последствия:

- orchestration не должен знать список weather providers;
- fallback можно добавить через `FallbackWeatherProvider`;
- domain получает нормализованный `WeatherReport` или отсутствие данных.

## D006. LLM ranking для MVP

Статус: принято.

Решение: ранжирование рекомендаций в MVP остается на стороне LLM.

Причина: объем данных небольшой, а ранжирование требует объяснения trade-offs: доступность, погода, безопасность, личные ограничения.

Последствия:

- код должен готовить качественный структурированный context для LLM;
- финальный ответ должен объяснять ранжирование;
- если качество станет нестабильным, scoring переносится в domain/application code.

## D007. Persistent sessions обязательны для MVP

Статус: принято.

Решение: сессии должны сохраняться между перезапусками приложения.

Причина: пользователь должен иметь возможность вернуться к прошлому диалогу и продолжить контекст.

Последствия:

- in-memory session store допустим только для тестов и временной разработки;
- рекомендуемый MVP storage - SQLite;
- `ChatUseCase` должен работать только через `SessionStore`.

## D008. Sky calendar и nature conditions откладываются после MVP

Статус: принято.

Решение: проверку текущих астрономических событий, видимых объектов и дополнительных природных условий не включать в первый MVP.

Причина: первый MVP должен сфокусироваться на надежном основном сценарии: понять пожелания пользователя, найти 3-5 подходящих мест и проверить погоду. Astro events и nature conditions расширяют ценность, но увеличивают количество внешних источников и edge cases.

Последствия:

- `SkyCalendarProvider` не является обязательным для первого MVP;
- `NatureConditionsProvider` не является обязательным для первого MVP;
- когда эти возможности появятся, их нужно оформлять через отдельные ports/adapters, а не прятать только в prompt.

## D009. Clarification-first UX

Статус: принято.

Решение: если пользователь дал только локацию, ассистент задает короткий уточняющий вопрос перед поиском. Если пользователь просит быстрый ответ без уточнений, агент продолжает с defaults и явно пишет предположения.

Причина: рекомендации сильно зависят от транспорта, радиуса, времени, безопасности и доступности.

Последствия:

- location остается минимально обязательным полем;
- transport/radius/time/safety/telescope являются важными, но не всегда blocking;
- policy должна быть выражена не только prompt-ом, но и проверяемой логикой.

## D010. Новые документы заменяют PROJECT_SPEC как source of truth

Статус: принято.

Решение: `ARCHITECTURE.md` и `decisions.md` становятся каноническими документами MVP.

Причина: старый `PROJECT_SPEC.md` содержит смешение целевой архитектуры, старых идей и текущих деталей. Новые документы короче и точнее фиксируют решения.

Последствия:

- при конфликте читать сначала `ARCHITECTURE.md`, затем `decisions.md`;
- `PROJECT_SPEC.md` можно позже удалить или переписать в product-only spec;
- README должен быть обновлен отдельно, чтобы не ссылаться на устаревший Google ADK подход.

## D011. Google ADK не является целевым решением MVP

Статус: принято.

Решение: не использовать Google ADK как целевую архитектуру MVP.

Причина: выбранный путь - PydanticAI-first. Старое описание ADK в README является устаревшим.

Последствия:

- README нужно привести в соответствие;
- Agent Engine deployment не является текущим архитектурным требованием.

## D012. Документация MVP ведется на русском

Статус: принято.

Решение: писать архитектурные документы MVP на русском, сохраняя имена компонентов и интерфейсов на английском.

Причина: так быстрее принимать решения на этапе MVP.

Последствия:

- позже документы можно перевести на английский;
- кодовые имена, class names и file names остаются на английском.

## D013. Pydantic Logfire как observability-система MVP

Статус: принято.

Решение: использовать Pydantic Logfire для tracing и observability MVP.

Причина: PydanticAI имеет нативную Logfire-интеграцию, а Logfire построен на OpenTelemetry. Это дает agent traces, model/tool spans, token/cost visibility, eval traces и возможность уйти в другой OTel-compatible backend без переписывания архитектуры.

Последствия:

- `logfire.configure()` и `logfire.instrument_pydantic_ai()` должны вызываться на уровне приложения/entrypoint;
- FastAPI и persistent storage можно инструментировать отдельно;
- custom spans нужны вокруг `ChatUseCase`, search/weather adapters и session store;
- domain layer остается без observability-зависимостей;
- prompts/history/secrets не должны бездумно попадать в traces.

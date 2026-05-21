import os
from pathlib import Path
from typing import Any

import logfire
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pydantic_ai.models.openai import OpenAIModel

from app.application.chat_use_case import ChatUseCase
from app.infrastructure.search.google_search import LLMSearchProvider
from app.infrastructure.session.in_memory_store import InMemorySessionStore
from app.infrastructure.weather.seven_timer import SevenTimerWeatherProvider
from app.orchestration.pydantic_ai_orchestrator import PydanticAIOrchestrator
from app.presentation.presenter import FastApiPresenter

# Configure Logfire observability
logfire.configure()
logfire.instrument_pydantic_ai()

# 1. Initialize the Pydantic AI Model (Nemotron via OpenRouter)
api_key = os.environ.get("OPENROUTER_API_KEY", "dummy_key")
model = OpenAIModel(
    "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

# 2. Initialize Ports / Infrastructure Adapters
search = LLMSearchProvider(model=model)
weather = SevenTimerWeatherProvider()
session_store = InMemorySessionStore()

# 3. Build Orchestrator
orchestrator = PydanticAIOrchestrator(
    model=model,
    search=search,
    weather=weather,
)

# 4. Build Application Use Case
chat_use_case = ChatUseCase(orchestrator=orchestrator, session_store=session_store)
presenter = FastApiPresenter()

# 5. FastAPI Setup
app = FastAPI(title="Lazy Stellar API")

logfire.instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str


@app.post("/chat")
async def chat_endpoint(req: ChatRequest) -> Any:
    """Entrypoint for the chat scenario."""
    try:
        response = chat_use_case.handle_message(req.session_id, req.message)
        return presenter.format_chat_response(response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> str:
    """Serves the 8-bit frontend directly."""
    index_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html not found")
    return index_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn

    # Allow running directly via python entrypoints/local_api.py
    uvicorn.run("entrypoints.local_api:app", host="0.0.0.0", port=8501, reload=True)

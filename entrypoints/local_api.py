from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.application.chat_use_case import ChatUseCase
from app.infrastructure.llm.nemotron_openrouter import NemotronOpenRouter
from app.infrastructure.search.google_search import LLMSearchProvider
from app.infrastructure.session.in_memory_store import InMemorySessionStore
from app.infrastructure.weather.seven_timer import SevenTimerWeatherProvider
from app.orchestration.graph import build_graph
from app.presentation.presenter import FastApiPresenter

# 1. Initialize Ports / Infrastructure Adapters
llm = NemotronOpenRouter()
search = LLMSearchProvider(llm=llm)
weather = SevenTimerWeatherProvider()
session_store = InMemorySessionStore()

# 2. Build Orchestrator
orchestrator = build_graph(search=search, weather=weather, llm=llm)

# 3. Build Application Use Case
chat_use_case = ChatUseCase(orchestrator=orchestrator, session_store=session_store)
presenter = FastApiPresenter()

# 4. FastAPI Setup
app = FastAPI(title="Lazy Stellar API")

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

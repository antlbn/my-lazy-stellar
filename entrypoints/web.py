from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from runtime.lifecycle import create_runtime

runtime = create_runtime()
agent_app = runtime.agent.to_web()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    try:
        yield
    finally:
        runtime.close()


app = FastAPI(lifespan=lifespan)
app.mount("/", agent_app)

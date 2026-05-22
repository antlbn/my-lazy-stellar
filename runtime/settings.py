import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agent import DEFAULT_MODEL

LogfireSendToLogfire = bool | Literal["if-token-present"] | None


@dataclass(frozen=True)
class Settings:
    model: str
    database_path: Path
    logfire_send_to_logfire: LogfireSendToLogfire
    capture_httpx: bool


def _load_logfire_send_to_logfire() -> LogfireSendToLogfire:
    value = os.getenv("LAZY_STELLAR_LOGFIRE_SEND_TO_LOGFIRE", "if-token-present")
    if value == "if-token-present":
        return "if-token-present"
    if value.lower() in {"1", "true", "yes", "on"}:
        return True
    if value.lower() in {"0", "false", "no", "off"}:
        return False
    return None


def load_settings() -> Settings:
    return Settings(
        model=os.getenv("LAZY_STELLAR_MODEL", DEFAULT_MODEL),
        database_path=Path(os.getenv("LAZY_STELLAR_DB_PATH", "sessions.db")),
        logfire_send_to_logfire=_load_logfire_send_to_logfire(),
        capture_httpx=os.getenv("LAZY_STELLAR_CAPTURE_HTTPX", "0") == "1",
    )

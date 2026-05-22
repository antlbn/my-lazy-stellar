import logfire

from storage.session import init_db

from .settings import Settings

_LOGFIRE_CONFIGURED = False


def configure_logfire(settings: Settings) -> None:
    global _LOGFIRE_CONFIGURED
    if _LOGFIRE_CONFIGURED:
        return

    logfire.configure(send_to_logfire=settings.logfire_send_to_logfire)
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=settings.capture_httpx)
    _LOGFIRE_CONFIGURED = True


def initialize_storage(settings: Settings) -> None:
    init_db(settings.database_path)

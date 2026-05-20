from app.application.responses import AssistantResponse


class FastApiPresenter:
    """Formats domain responses for the FastAPI endpoints."""

    def format_chat_response(self, response: AssistantResponse) -> dict[str, str]:
        """Convert the AssistantResponse into a JSON-serializable dictionary."""
        return {"response": response.text}

from typing import Any

from app.application.responses import AssistantResponse
from app.domain.models import UserContext
from app.orchestration.state import AstroState
from app.ports.session_store import Session, SessionStore


class ChatUseCase:
    """The main entrypoint for the chat scenario.

    Coordinates loading session history, invoking the orchestrator,
    and saving the resulting session state.
    """

    def __init__(self, orchestrator: Any, session_store: SessionStore) -> None:
        self.orchestrator = orchestrator
        self.session_store = session_store

    def handle_message(self, session_id: str, text: str) -> AssistantResponse:
        # 1. Load or create session
        session = self.session_store.load(session_id)
        if not session:
            session = Session(session_id=session_id)

        # 2. Update context heuristically for MVP
        # (In a real app, an LLM extraction node would update this state dynamically)
        context = session.state.get("context")
        if not context:
            # If there's no context at all, assume this first message provides the location.
            context = UserContext(location=text)
            session.state["context"] = context

        # 3. Prepare initial state for graph
        # Since we use `operator.add` for messages in AstroState,
        # providing the full list will replace the history if we don't use MemorySaver.
        # Wait, if we use operator.add and invoke without MemorySaver, it just adds them together.
        # We will pass the full list so the LLM nodes have access to the whole history.
        state_input: AstroState = {
            "session_id": session_id,
            "messages": [*session.messages, {"role": "user", "content": text}],
            "context": context,
            "spots": session.state.get("spots", []),
            "recommendations": session.state.get("recommendations", []),
            "final_answer": "",
        }

        # 4. Execute orchestrator
        final_state = self.orchestrator.invoke(state_input)

        # 5. Save updated state back to session store
        session.messages = final_state["messages"]
        session.state["context"] = final_state["context"]
        session.state["spots"] = final_state.get("spots", [])
        session.state["recommendations"] = final_state.get("recommendations", [])
        self.session_store.save(session)

        # 6. Return standard response
        # The last message in the list should be the assistant's reply.
        reply_text = session.messages[-1]["content"] if session.messages else ""
        return AssistantResponse(text=reply_text)

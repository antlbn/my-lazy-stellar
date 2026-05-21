from typing import Any

from app.application.responses import AssistantResponse, ChatAgentOutput
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

        # 2. Add new user message to session
        messages = [*session.messages, {"role": "user", "content": text}]

        # 3. Execute orchestrator (Pydantic AI)
        agent_output: ChatAgentOutput = self.orchestrator.handle(
            session_id=session_id,
            messages=messages,
        )

        # 4. Save updated state back to session store
        messages.append({"role": "assistant", "content": agent_output.answer})
        session.messages = messages
        
        session.state["recommendations"] = [
            r.model_dump() for r in agent_output.recommendations
        ]
        
        self.session_store.save(session)

        # 5. Return standard response
        return AssistantResponse(
            text=agent_output.answer,
            agent_output=agent_output,
        )

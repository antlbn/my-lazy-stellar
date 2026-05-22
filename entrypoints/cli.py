import asyncio
import uuid

import logfire
from pydantic_ai.messages import ModelMessagesTypeAdapter

from runtime.lifecycle import create_runtime
from storage.session import load_session, save_session


async def main() -> None:
    runtime = create_runtime()

    print("Welcome to Lazy Stellar!")
    session_id = input("Enter session ID (or leave blank for new): ").strip()
    if not session_id:
        session_id = str(uuid.uuid4())
        print(f"Created new session: {session_id}")

    raw_history = load_session(session_id, runtime.settings.database_path)
    message_history = None
    if raw_history:
        message_history = ModelMessagesTypeAdapter.validate_python(raw_history)
        print("Loaded previous history.")

    try:
        while True:
            try:
                prompt = input("\nYou: ").strip()
                if not prompt:
                    continue
                if prompt.lower() in ["exit", "quit"]:
                    break

                with logfire.span("chat_interaction"):
                    result = await runtime.agent.run(
                        prompt,
                        message_history=message_history,
                        conversation_id=session_id,
                    )

                    print(f"\nLazy Stellar: {result.output}")

                    message_history = result.all_messages()
                    save_session(
                        session_id,
                        ModelMessagesTypeAdapter.dump_python(message_history),
                        runtime.settings.database_path,
                    )

            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                logfire.exception("Error processing chat: {e}", e=e)
                print(f"Error: {e}")
    finally:
        runtime.close()


if __name__ == "__main__":
    asyncio.run(main())

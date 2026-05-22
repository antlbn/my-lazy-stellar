import asyncio
import uuid

import logfire
from pydantic_ai.messages import ModelMessagesTypeAdapter

from agent import agent
from storage.session import init_db, load_session, save_session

# 1. Configure Logfire first!
logfire.configure()
# 2. Instrument pydantic_ai
logfire.instrument_pydantic_ai()
# 3. Instrument httpx
logfire.instrument_httpx()
# Note: SQLite instrumentation could be added via OpenTelemetry if needed


async def main():
    init_db()

    print("Welcome to Lazy Stellar!")
    session_id = input("Enter session ID (or leave blank for new): ").strip()
    if not session_id:
        session_id = str(uuid.uuid4())
        print(f"Created new session: {session_id}")

    raw_history = load_session(session_id)
    message_history = None
    if raw_history:
        message_history = ModelMessagesTypeAdapter.validate_python(raw_history)
        print("Loaded previous history.")

    while True:
        try:
            prompt = input("\nYou: ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit"]:
                break

            with logfire.span("chat_interaction"):
                result = await agent.run(
                    prompt, message_history=message_history, conversation_id=session_id
                )

                print(f"\nLazy Stellar: {result.output.message}")
                if result.output.spots_found > 0:
                    print(f"[Found {result.output.spots_found} spots]")

                message_history = result.all_messages()
                save_session(
                    session_id, ModelMessagesTypeAdapter.dump_python(message_history)
                )

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            logfire.exception("Error processing chat: {e}", e=e)
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

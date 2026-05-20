import os

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.ports.llm_provider import LLMProvider, LLMProviderError


class NemotronOpenRouter(LLMProvider):
    """Adapter for the Nemotron LLM via OpenRouter."""

    def __init__(self) -> None:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment variables")

        self.llm = ChatOpenAI(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=SecretStr(api_key),
        )

    def chat(self, messages: list[dict[str, str]]) -> str:
        lc_msgs: list[BaseMessage] = []
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")

            if role == "system":
                lc_msgs.append(SystemMessage(content=content))
            elif role == "user":
                lc_msgs.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_msgs.append(AIMessage(content=content))
            else:
                lc_msgs.append(HumanMessage(content=content))

        try:
            response = self.llm.invoke(lc_msgs)
            return str(response.content)
        except Exception as e:
            raise LLMProviderError(f"OpenRouter LLM call failed: {e}") from e

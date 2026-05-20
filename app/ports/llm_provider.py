"""LLMProvider port — abstract interface for chat-model access."""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Minimal interface for calling a chat LLM.

    Infrastructure adapters (Nemotron/OpenRouter, Gemini, …) implement this.
    The orchestration layer uses it only through this port.
    """

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a list of messages and return the assistant reply as a string.

        Args:
            messages: List of dicts with keys ``"role"`` (``"system"`` /
                      ``"user"`` / ``"assistant"``) and ``"content"``.

        Returns:
            The model's reply text.

        Raises:
            LLMProviderError: on network or model errors.
        """
        ...


class LLMProviderError(Exception):
    """Raised when an LLM provider call fails."""

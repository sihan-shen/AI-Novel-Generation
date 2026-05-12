from abc import ABC, abstractmethod
from typing import Any


class LLMResponse:
    def __init__(self, content: str, usage: dict | None = None):
        self.content = content
        self.usage = usage or {}


class LLMAdapter(ABC):
    @abstractmethod
    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        ...


def get_adapter() -> LLMAdapter:
    from app.config import settings
    if settings.llm_provider == "claude":
        from app.llm.claude_adapter import ClaudeAdapter
        return ClaudeAdapter(api_key=settings.claude_api_key)
    elif settings.llm_provider == "openai":
        from app.llm.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(api_key=settings.openai_api_key)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

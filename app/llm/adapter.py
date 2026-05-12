from abc import ABC, abstractmethod
from typing import Any
from datetime import datetime


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


def record_usage(db: Any, model: str, usage: dict, scenario: str = ""):
    """Record token usage to database."""
    from app.models.token_usage import TokenUsage
    if not usage:
        return
    record = TokenUsage(
        model=model,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        scenario=scenario,
    )
    db.add(record)
    db.commit()

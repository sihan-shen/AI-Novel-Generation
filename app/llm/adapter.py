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


def get_adapter(db: Any = None) -> LLMAdapter:
    from app.config import settings

    provider = settings.llm_provider
    claude_key = settings.claude_api_key
    openai_key = settings.openai_api_key
    claude_model = "claude-sonnet-4-6"
    openai_model = "gpt-4o"

    # DB config overrides .env when available
    if db is not None:
        from app.services.config_service import ConfigService
        cfg = ConfigService.get_all(db)
        if cfg.get("llm_provider"):
            provider = cfg["llm_provider"]
        if cfg.get("claude_api_key"):
            claude_key = cfg["claude_api_key"]
        if cfg.get("openai_api_key"):
            openai_key = cfg["openai_api_key"]
        if cfg.get("claude_model"):
            claude_model = cfg["claude_model"]
        if cfg.get("openai_model"):
            openai_model = cfg["openai_model"]

    if provider == "claude":
        from app.llm.claude_adapter import ClaudeAdapter
        return ClaudeAdapter(api_key=claude_key, model=claude_model)
    elif provider == "openai":
        from app.llm.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(api_key=openai_key, model=openai_model)
    raise ValueError(f"Unknown LLM provider: {provider}")


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

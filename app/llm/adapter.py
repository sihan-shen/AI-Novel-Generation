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


def get_adapter(db: Any = None) -> LLMAdapter:
    from app.config import settings

    provider = settings.llm_provider
    api_key = ""
    base_url = ""
    model = ""

    if db is not None:
        from app.services.config_service import ConfigService
        cfg = ConfigService.get_all(db)
        provider = cfg.get("llm_provider", provider)
        api_key = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "")
        model = cfg.get("model", "")
    else:
        api_key = settings.claude_api_key or settings.openai_api_key
        model = "claude-sonnet-4-6"

    if not model:
        from app.llm.provider_registry import PROVIDERS
        info = PROVIDERS.get(provider)
        model = info.default_model if info else ""

    if provider == "claude":
        from app.llm.claude_adapter import ClaudeAdapter
        return ClaudeAdapter(api_key=api_key or settings.claude_api_key, model=model)
    elif provider == "openai":
        from app.llm.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(api_key=api_key or settings.openai_api_key, model=model)
    elif provider == "ollama":
        from app.llm.openai_adapter import OpenAIAdapter
        base = (base_url or "http://localhost:11434").rstrip("/") + "/v1"
        return OpenAIAdapter(api_key="ollama", model=model, base_url=base)
    elif provider == "gemini":
        from app.llm.openai_adapter import OpenAIAdapter
        base = f"https://generativelanguage.googleapis.com/v1beta/openai/"
        return OpenAIAdapter(api_key=api_key, model=model, base_url=base)
    elif provider == "custom":
        from app.llm.openai_adapter import OpenAIAdapter
        return OpenAIAdapter(api_key=api_key, model=model, base_url=base_url)
    raise ValueError(f"Unknown LLM provider: {provider}")


def record_usage(db: Any, model: str, usage: dict, scenario: str = ""):
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

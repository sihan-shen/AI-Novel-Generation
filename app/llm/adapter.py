import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class LLMResponse:
    def __init__(self, content: str, usage: dict | None = None):
        self.content = content
        self.usage = usage or {}


@dataclass
class ToolUseResponse:
    """Response from an LLM turn that may include tool calls."""
    content: str
    tool_calls: list[dict]
    finish_reason: str
    usage: dict


@dataclass
class UsageRecord:
    """Parameters for recording an AI call to the database."""
    model: str
    usage: dict
    scenario: str = ""
    prompt: str = ""
    response: str = ""
    duration_ms: int | None = None
    project_id: str | None = None


class LLMAdapter(ABC):
    supports_native_tools: bool = False

    @abstractmethod
    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        ...

    @abstractmethod
    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        ...

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        stream_callback: Callable[[str], None] | None,
    ) -> ToolUseResponse:
        ...


def get_adapter(db: Any = None) -> LLMAdapter:
    from app.config import settings
    from app.llm.claude_adapter import ClaudeAdapter
    from app.llm.openai_adapter import OpenAIAdapter

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

    provider = provider.lower()

    if not model:
        from app.llm.provider_registry import PROVIDERS
        info = PROVIDERS.get(provider)
        model = info.default_model if info else ""

    _adapter_map: dict[str, tuple[type[LLMAdapter], str | None]] = {
        "claude": (ClaudeAdapter, None),
        "openai": (OpenAIAdapter, None),
        "ollama": (OpenAIAdapter, "ollama"),
        "gemini": (OpenAIAdapter, "gemini"),
        "deepseek": (OpenAIAdapter, "deepseek"),
        "custom": (OpenAIAdapter, "custom"),
    }

    if provider not in _adapter_map:
        raise ValueError(f"Unknown LLM provider: {provider}")

    adapter_cls, base_strategy = _adapter_map[provider]

    if adapter_cls is ClaudeAdapter:
        return ClaudeAdapter(api_key=api_key or settings.claude_api_key, model=model)

    if base_strategy == "ollama":
        resolved_base = (base_url or "http://localhost:11434").rstrip("/") + "/v1"
        return OpenAIAdapter(api_key="ollama", model=model, base_url=resolved_base)
    elif base_strategy == "gemini":
        return OpenAIAdapter(
            api_key=api_key, model=model,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    elif base_strategy == "deepseek":
        return OpenAIAdapter(
            api_key=api_key, model=model, base_url="https://api.deepseek.com/v1",
        )
    elif base_strategy == "custom":
        return OpenAIAdapter(api_key=api_key, model=model, base_url=base_url)
    else:
        return OpenAIAdapter(api_key=api_key or settings.openai_api_key, model=model)


def record_usage(db: Any, model: str, usage: dict, scenario: str = "",
                 prompt: str = "", response: str = "", duration_ms: int | None = None,
                 project_id: str | None = None):
    """Record an AI call. No-op if usage is empty."""
    from app.models.ai_call import AICall
    if not usage:
        return
    rec = UsageRecord(
        model=model,
        usage=usage,
        scenario=scenario,
        prompt=prompt or "",
        response=response or "",
        duration_ms=duration_ms,
        project_id=project_id,
    )
    record = AICall(
        model=rec.model,
        input_tokens=rec.usage.get("input_tokens", 0),
        output_tokens=rec.usage.get("output_tokens", 0),
        scenario=rec.scenario,
        prompt=rec.prompt,
        response=rec.response,
        duration_ms=rec.duration_ms,
        status="success",
        project_id=rec.project_id,
    )
    try:
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "record_usage failed for scenario=%s project=%s",
            rec.scenario, rec.project_id,
        )

"""Provider registry — metadata, preset models, and remote model listing."""

from dataclasses import dataclass, field


@dataclass
class ProviderInfo:
    id: str
    label: str
    has_model_list_api: bool
    needs_api_key: bool
    needs_base_url: bool
    preset_models: list[str] = field(default_factory=list)
    default_model: str = ""
    api_key_label: str = "API Key"
    base_url_label: str = "API 地址"
    base_url_placeholder: str = ""


PROVIDERS: dict[str, ProviderInfo] = {
    "claude": ProviderInfo(
        id="claude", label="Claude (Anthropic)", has_model_list_api=False,
        needs_api_key=True, needs_base_url=False,
        preset_models=["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
        default_model="claude-sonnet-4-6", api_key_label="Claude API Key",
    ),
    "openai": ProviderInfo(
        id="openai", label="OpenAI", has_model_list_api=True,
        needs_api_key=True, needs_base_url=False,
        preset_models=["gpt-4o", "gpt-4o-mini", "o3-mini", "o1"],
        default_model="gpt-4o", api_key_label="OpenAI API Key",
    ),
    "ollama": ProviderInfo(
        id="ollama", label="Ollama (本地)", has_model_list_api=True,
        needs_api_key=False, needs_base_url=True,
        preset_models=["llama3", "mistral", "qwen2.5", "gemma2"],
        default_model="llama3",
        base_url_label="Ollama 地址", base_url_placeholder="http://localhost:11434",
    ),
    "gemini": ProviderInfo(
        id="gemini", label="Google Gemini", has_model_list_api=False,
        needs_api_key=True, needs_base_url=False,
        preset_models=["gemini-2.5-flash", "gemini-2.5-pro"],
        default_model="gemini-2.5-flash", api_key_label="Gemini API Key",
    ),
    "deepseek": ProviderInfo(
        id="deepseek", label="DeepSeek", has_model_list_api=False,
        needs_api_key=True, needs_base_url=False,
        preset_models=["deepseek-chat", "deepseek-reasoner"],
        default_model="deepseek-chat", api_key_label="DeepSeek API Key",
    ),
    "custom": ProviderInfo(
        id="custom", label="自定义 (OpenAI 兼容)", has_model_list_api=True,
        needs_api_key=True, needs_base_url=True,
        preset_models=[], default_model="",
        api_key_label="API Key", base_url_label="API 地址",
        base_url_placeholder="https://api.example.com/v1",
    ),
}


async def fetch_models(provider: str, api_key: str = "", base_url: str = "") -> list[str]:
    """Fetch available models from the provider's API. Returns list of model IDs."""
    import httpx

    provider = provider.lower()

    if provider == "openai":
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            return [m["id"] for m in data.get("data", []) if not m["id"].startswith("ft:")]

    elif provider == "ollama":
        base = (base_url or "http://localhost:11434").rstrip("/")
        url = f"{base}/api/tags"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            return [m["name"] for m in data.get("models", [])]

    elif provider == "custom":
        base = base_url.rstrip("/")
        url = f"{base}/models"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            return [m["id"] for m in data.get("data", [])]

    # Providers without a model list API return presets
    info = PROVIDERS.get(provider)
    return list(info.preset_models) if info else []

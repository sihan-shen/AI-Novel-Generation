from typing import AsyncGenerator
from openai import AsyncOpenAI
from app.llm.adapter import LLMAdapter, LLMResponse


class OpenAIAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str | None = None):
        self.model = model
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs) if api_key else None

    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        if not self.client:
            return LLMResponse(content="[LLM 未配置]", usage={})
        response = await self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            usage={"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens} if response.usage else {}
        )

    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        if not self.client:
            yield "[LLM 未配置]"
            return
        stream = await self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

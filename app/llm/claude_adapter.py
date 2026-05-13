from typing import AsyncGenerator
from anthropic import AsyncAnthropic
from app.llm.adapter import LLMAdapter, LLMResponse


class ClaudeAdapter(LLMAdapter):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key) if api_key else None

    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        if not self.client:
            return LLMResponse(content="[LLM 未配置]", usage={})
        system_msg, api_messages = self._split_messages(messages)
        response = await self.client.messages.create(
            model=kwargs.get("model", self.model),
            system=system_msg,
            messages=api_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )
        content = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(content=content, usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens})

    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        if not self.client:
            yield "[LLM 未配置]"
            return
        system_msg, api_messages = self._split_messages(messages)
        async with self.client.messages.stream(
            model=kwargs.get("model", self.model),
            system=system_msg,
            messages=api_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    def _split_messages(self, messages: list[dict]) -> tuple[str | None, list[dict]]:
        system_msg = None
        api_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg["content"]
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})
        return system_msg, api_messages

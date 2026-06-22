import json
import logging
from collections.abc import AsyncGenerator, Callable

from openai import AsyncOpenAI

from app.llm.adapter import LLMAdapter, LLMResponse, ToolUseResponse

logger = logging.getLogger(__name__)


class OpenAIAdapter(LLMAdapter):
    supports_native_tools = True

    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str | None = None):
        self.model = model
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs) if api_key else None  # type: ignore[arg-type]

    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        if not self.client:
            return LLMResponse(content="[LLM 未配置]", usage={})
        response = await self.client.chat.completions.create(
            model=kwargs.get("model", self.model),
            messages=messages,  # type: ignore[arg-type]
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            usage={"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens} if response.usage else {}  # noqa: E501
        )

    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:  # type: ignore[override]
        """Stream text deltas.

        After the stream closes, surfaces usage via optional *usage_callback*.

        If *usage_callback* is provided in ``**kwargs``, it is called once with a dict
        ``{"input_tokens": int, "output_tokens": int}`` after all text chunks have been
        yielded. For OpenAI this requires ``stream_options={"include_usage": True}``.
        """
        if not self.client:
            yield "[LLM 未配置]"
            return
        usage_callback: Callable[[dict], None] | None = kwargs.get("usage_callback")
        stream = await self.client.chat.completions.create(  # type: ignore[call-overload]
            model=kwargs.get("model", self.model),
            messages=messages,  # type: ignore[arg-type]
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            if usage_callback is not None and chunk.usage is not None:
                usage_callback({
                    "input_tokens": chunk.usage.prompt_tokens,
                    "output_tokens": chunk.usage.completion_tokens,
                })

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        stream_callback: Callable[[str], None] | None,
    ) -> ToolUseResponse:
        if not self.client:
            return ToolUseResponse(content="[LLM 未配置]", tool_calls=[], finish_reason="error", usage={})  # noqa: E501

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,  # type: ignore[arg-type]
        )

        message = response.choices[0].message
        content = message.content or ""
        tool_calls = []
        if getattr(message, "tool_calls", None):
            for tc in message.tool_calls:  # type: ignore[union-attr]
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}  # type: ignore[union-attr]
                tool_calls.append({"name": tc.function.name, "args": args})  # type: ignore[union-attr]

        finish_reason = "tool_calls" if tool_calls else "stop"
        usage = {"input_tokens": response.usage.prompt_tokens, "output_tokens": response.usage.completion_tokens} if response.usage else {}  # noqa: E501

        return ToolUseResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )

logger.info("Module %s loaded", __name__)

import logging
from collections.abc import AsyncGenerator, Callable

from anthropic import AsyncAnthropic

from app.llm.adapter import LLMAdapter, LLMResponse, ToolUseResponse
from app.llm.exceptions import LLMToolParseError

logger = logging.getLogger(__name__)


class ClaudeAdapter(LLMAdapter):
    supports_native_tools = True

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key) if api_key else None

    async def generate(self, messages: list[dict], **kwargs) -> LLMResponse:
        if not self.client:
            return LLMResponse(content="[LLM 未配置]", usage={})
        system_msg, api_messages = self._split_messages(messages)
        response = await self.client.messages.create(
            model=kwargs.get("model", self.model),
            system=system_msg,  # type: ignore[arg-type]
            messages=api_messages,  # type: ignore[arg-type]
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )
        content = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(content=content, usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens})  # noqa: E501

    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:  # type: ignore[override]
        """Stream text deltas.

        After the stream closes, surfaces usage via optional *usage_callback*.

        If *usage_callback* is provided in ``**kwargs``, it is called once with a dict
        ``{"input_tokens": int, "output_tokens": int}`` after all text chunks have been
        yielded. This preserves backward compatibility for callers that expect only
        ``str`` chunks.
        """
        if not self.client:
            yield "[LLM 未配置]"
            return
        system_msg, api_messages = self._split_messages(messages)
        usage_callback: Callable[[dict], None] | None = kwargs.get("usage_callback")
        async with self.client.messages.stream(
            model=kwargs.get("model", self.model),
            system=system_msg,  # type: ignore[arg-type]
            messages=api_messages,  # type: ignore[arg-type]
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        ) as stream:
            async for text in stream.text_stream:
                yield text
            if usage_callback is not None:
                final = await stream.get_final_message()
                if final.usage is not None:
                    usage_callback({
                        "input_tokens": final.usage.input_tokens,
                        "output_tokens": final.usage.output_tokens,
                    })

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

        system_msg, api_messages = self._split_messages(messages)
        response = await self.client.messages.create(  # type: ignore[call-overload]
            model=self.model,
            system=system_msg,  # type: ignore[arg-type]
            messages=api_messages,  # type: ignore[arg-type]
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            tool_choice="auto",
        )

        content_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content_parts.append(block.text)
                if stream_callback is not None:
                    stream_callback(block.text)
            elif block.type == "tool_use":
                if not hasattr(block, "name") or not hasattr(block, "input"):
                    raise LLMToolParseError(f"Malformed tool_use block: missing name or input — {block!r}")  # noqa: E501
                tool_calls.append({"name": block.name, "args": block.input})

        finish_reason = "tool_use" if tool_calls else "stop"
        usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens} if response.usage else {}  # noqa: E501

        return ToolUseResponse(
            content="".join(content_parts),
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )

logger.info("Module %s loaded", __name__)

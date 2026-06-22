"""Tests for native tool-use API in LLM adapters + stream usage capture.

Acceptance criteria:
  a) Claude generate_with_tools parses tool_use blocks correctly.
  b) Claude generate_with_tools raises LLMToolParseError on malformed tool_use.
  c) OpenAI generate_with_tools parses message.tool_calls correctly.
  d) REGRESSION: generate() and generate_stream() still return text for both adapters.
  e) Stream usage capture: Claude generate_stream surfaces usage via callback.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.claude_adapter import ClaudeAdapter
from app.llm.exceptions import LLMToolParseError
from app.llm.openai_adapter import OpenAIAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claude_block(block_type, **kwargs):
    """Build a minimal Anthropic content-block mock."""
    m = MagicMock()
    m.type = block_type
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m


def _make_openai_tool_call(name, arguments):
    """Build a minimal OpenAI tool_calls entry mock."""
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


# ---------------------------------------------------------------------------
# a) Claude — valid tool_use block
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claude_generate_with_tools_parses_tool_use():
    """Mock AsyncAnthropic returns a tool_use block → parsed into tool_calls."""
    adapter = ClaudeAdapter(api_key="fake-key", model="claude-3-5-sonnet")

    mock_block = _make_claude_block(
        "tool_use",
        name="lookup_settings",
        input={"keywords": ["x"]},
    )
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)

    adapter.client = MagicMock()
    adapter.client.messages.create = AsyncMock(return_value=mock_response)

    result = await adapter.generate_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"name": "lookup_settings", "description": "...", "parameters": {}}],
        temperature=0.7,
        max_tokens=1024,
        stream_callback=None,
    )

    assert result.content == ""
    assert result.tool_calls == [{"name": "lookup_settings", "args": {"keywords": ["x"]}}]
    assert result.finish_reason == "tool_use"
    assert result.usage == {"input_tokens": 10, "output_tokens": 20}


# ---------------------------------------------------------------------------
# b) Claude — malformed tool_use block (missing input)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claude_generate_with_tools_missing_input_raises():
    """Mock returns tool_use block without `input` → LLMToolParseError."""
    adapter = ClaudeAdapter(api_key="fake-key", model="claude-3-5-sonnet")

    mock_block = _make_claude_block("tool_use", name="lookup_settings")
    # Deliberately omit `input` attribute
    del mock_block.input

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.usage = MagicMock(input_tokens=5, output_tokens=5)

    adapter.client = MagicMock()
    adapter.client.messages.create = AsyncMock(return_value=mock_response)

    with pytest.raises(LLMToolParseError):
        await adapter.generate_with_tools(
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
            temperature=0.7,
            max_tokens=1024,
            stream_callback=None,
        )


# ---------------------------------------------------------------------------
# c) OpenAI — valid tool_calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openai_generate_with_tools_parses_tool_calls():
    """Mock AsyncOpenAI returns message.tool_calls → parsed."""
    adapter = OpenAIAdapter(api_key="fake-key", model="gpt-4o")

    mock_tool_call = _make_openai_tool_call("f", '{"a": 1}')
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_message.content = None

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=15, completion_tokens=25)

    adapter.client = MagicMock()
    adapter.client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await adapter.generate_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"name": "f", "description": "...", "parameters": {}}],
        temperature=0.7,
        max_tokens=1024,
        stream_callback=None,
    )

    assert result.content == ""
    assert result.tool_calls == [{"name": "f", "args": {"a": 1}}]
    assert result.finish_reason == "tool_calls"
    assert result.usage == {"input_tokens": 15, "output_tokens": 25}


# ---------------------------------------------------------------------------
# d) REGRESSION: generate() and generate_stream() still return text
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claude_generate_still_returns_text():
    """Existing text-generation path on Claude adapter is untouched."""
    adapter = ClaudeAdapter(api_key="fake-key", model="claude-3-5-sonnet")

    mock_block = _make_claude_block("text", text="Hello world")
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.usage = MagicMock(input_tokens=5, output_tokens=5)

    adapter.client = MagicMock()
    adapter.client.messages.create = AsyncMock(return_value=mock_response)

    result = await adapter.generate(messages=[{"role": "user", "content": "hi"}])
    assert result.content == "Hello world"


@pytest.mark.asyncio
async def test_claude_generate_stream_still_yields_text():
    """Existing streaming path on Claude adapter yields text chunks."""
    adapter = ClaudeAdapter(api_key="fake-key", model="claude-3-5-sonnet")

    mock_stream = MagicMock()
    mock_stream.text_stream = _async_iter(["Hello", " world"])
    mock_stream.get_final_message = AsyncMock(return_value=MagicMock(usage=MagicMock(input_tokens=3, output_tokens=4)))

    adapter.client = MagicMock()
    adapter.client.messages.stream = MagicMock(return_value=_async_context_manager(mock_stream))

    chunks = []
    async for chunk in adapter.generate_stream(messages=[{"role": "user", "content": "hi"}]):
        chunks.append(chunk)
    assert chunks == ["Hello", " world"]


@pytest.mark.asyncio
async def test_openai_generate_still_returns_text():
    """Existing text-generation path on OpenAI adapter is untouched."""
    adapter = OpenAIAdapter(api_key="fake-key", model="gpt-4o")

    mock_message = MagicMock()
    mock_message.content = "Hello world"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=5)

    adapter.client = MagicMock()
    adapter.client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await adapter.generate(messages=[{"role": "user", "content": "hi"}])
    assert result.content == "Hello world"


@pytest.mark.asyncio
async def test_openai_generate_stream_still_yields_text():
    """Existing streaming path on OpenAI adapter yields text chunks."""
    adapter = OpenAIAdapter(api_key="fake-key", model="gpt-4o")

    async def _mock_stream():
        deltas = ["Hello", " world"]
        for d in deltas:
            chunk = MagicMock()
            chunk.choices = [MagicMock(delta=MagicMock(content=d))]
            yield chunk

    adapter.client = MagicMock()
    adapter.client.chat.completions.create = AsyncMock(return_value=_mock_stream())

    chunks = []
    async for chunk in adapter.generate_stream(messages=[{"role": "user", "content": "hi"}]):
        chunks.append(chunk)
    assert chunks == ["Hello", " world"]


# ---------------------------------------------------------------------------
# e) Stream usage capture — Claude
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claude_generate_stream_surfaces_usage_via_callback():
    """After streaming text, Claude adapter calls usage_callback with usage dict."""
    adapter = ClaudeAdapter(api_key="fake-key", model="claude-3-5-sonnet")

    mock_stream = MagicMock()
    mock_stream.text_stream = _async_iter(["Once", " upon"])
    mock_stream.get_final_message = AsyncMock(
        return_value=MagicMock(usage=MagicMock(input_tokens=7, output_tokens=8))
    )

    adapter.client = MagicMock()
    adapter.client.messages.stream = MagicMock(return_value=_async_context_manager(mock_stream))

    captured_usage = {}

    def usage_callback(usage):
        captured_usage.update(usage)

    chunks = []
    async for chunk in adapter.generate_stream(
        messages=[{"role": "user", "content": "tell a story"}],
        usage_callback=usage_callback,
    ):
        chunks.append(chunk)

    assert chunks == ["Once", " upon"]
    assert captured_usage == {"input_tokens": 7, "output_tokens": 8}


@pytest.mark.asyncio
async def test_openai_generate_stream_surfaces_usage_via_callback():
    """After streaming text, OpenAI adapter calls usage_callback with usage dict."""
    adapter = OpenAIAdapter(api_key="fake-key", model="gpt-4o")

    async def _mock_stream():
        # Regular text chunks
        for text in ["Hello", " world"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock(delta=MagicMock(content=text))]
            chunk.usage = None
            yield chunk
        # Final usage chunk
        final = MagicMock()
        final.choices = []
        final.usage = MagicMock(prompt_tokens=6, completion_tokens=7)
        yield final

    adapter.client = MagicMock()
    adapter.client.chat.completions.create = AsyncMock(return_value=_mock_stream())

    captured_usage = {}

    def usage_callback(usage):
        captured_usage.update(usage)

    chunks = []
    async for chunk in adapter.generate_stream(
        messages=[{"role": "user", "content": "hi"}],
        usage_callback=usage_callback,
    ):
        chunks.append(chunk)

    assert chunks == ["Hello", " world"]
    assert captured_usage == {"input_tokens": 6, "output_tokens": 7}


# ---------------------------------------------------------------------------
# Capability flag
# ---------------------------------------------------------------------------

def test_claude_supports_native_tools():
    assert ClaudeAdapter(api_key="fake-key").supports_native_tools is True


def test_openai_supports_native_tools():
    assert OpenAIAdapter(api_key="fake-key").supports_native_tools is True


# ---------------------------------------------------------------------------
# Internal helpers for async mocking
# ---------------------------------------------------------------------------

async def _async_iter(items):
    for item in items:
        yield item


class _AsyncContextManager:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *args):
        pass


def _async_context_manager(value):
    return _AsyncContextManager(value)

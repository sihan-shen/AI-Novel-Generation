"""Agent base classes: AgentConfig, Tool, AgentStep, AgentRunResult."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentConfig:
    system_prompt: str
    tools: list[Tool]
    model: str = ""
    temperature: float = 0.7
    max_steps: int = 15
    token_budget: int = 100_000


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Any]
    confirm_before: bool = False
    idempotent: bool = True


@dataclass
class AgentStep:
    thought: str
    tool_name: str | None
    tool_args: dict | None
    result: str
    token_usage: dict = field(default_factory=dict)


@dataclass
class AgentRunResult:
    steps: list[AgentStep]
    output: str
    blackboard_changes: dict
    status: str  # completed | max_steps_reached | budget_exceeded | error | cancelled | handoff
    error_code: str | None = None
    retry_count: int = 0


import asyncio
import json
import logging
import time

from sqlalchemy.orm import Session

from app.agents.protocols import BlackboardProtocol, LLMAdapterProtocol
from app.llm.adapter import record_usage

logger = logging.getLogger(__name__)


async def run_agent(
    config: AgentConfig,
    blackboard: BlackboardProtocol,
    adapter: LLMAdapterProtocol,
    db: Session | None = None,
    agent_type: str = "",
) -> AgentRunResult:
    """Execute the agent tool-calling loop against the given blackboard."""
    from uuid import uuid4

    from app.llm.adapter import LLMResponse
    from app.llm.exceptions import LLMToolParseError

    def _try_record_usage(usage: dict, duration_ms: int) -> None:
        if db is None or not usage:
            return
        try:
            record_usage(
                db,
                adapter.model,
                usage,
                scenario=f"agent_{agent_type}" if agent_type else "agent",
                duration_ms=duration_ms,
                project_id=blackboard.project_id,
            )
        except Exception as e:
            logger.warning(f"record_usage failed: {e}")

    messages = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": blackboard.get_context_for("agent")},
    ]

    use_native_tools = getattr(adapter, "supports_native_tools", False)

    steps: list[AgentStep] = []
    malformed_count = 0
    llm_error_count = 0
    total_tokens = 0

    for step_num in range(1, config.max_steps + 1):
        if total_tokens > config.token_budget:
            return AgentRunResult(
                steps=steps, output="", blackboard_changes={},
                status="budget_exceeded", error_code="budget_exceeded",
                retry_count=llm_error_count,
            )

        if use_native_tools:
            try:
                from app.llm.adapter import ToolUseResponse
                t0 = time.monotonic()
                response: ToolUseResponse = await adapter.generate_with_tools(
                    messages,
                    tools=[{"name": t.name, "description": t.description, "parameters": t.parameters} for t in config.tools],  # noqa: E501
                    temperature=config.temperature,
                    max_tokens=4096,
                    stream_callback=lambda chunk, _step=step_num: blackboard.emit_event({"type": "text_delta", "content": chunk, "sequence": _step}),  # noqa: E501
                )
                _try_record_usage(response.usage, int((time.monotonic() - t0) * 1000))
            except (LLMToolParseError, NotImplementedError):
                use_native_tools = False
                if "Available tools:" not in messages[0]["content"]:
                    tool_schema_desc = _build_tool_schema_description(config.tools)
                    messages[0]["content"] += (
                        "\n\nYou MUST respond with valid JSON exactly matching one of these formats:\n"  # noqa: E501
                        '{"thought": "<reasoning>", "tool": "<tool_name>", "args": {...}}\n'
                        '{"action": "finish", "summary": "<final summary>"}\n'
                        '{"action": "handoff", "summary": "<handoff summary>"}\n\n'
                        f"Available tools:\n{tool_schema_desc}"
                    )
                continue
            except Exception as e:
                llm_error_count, abort = await _handle_llm_error(llm_error_count, e, steps)
                if abort is not None:
                    return abort
                continue

            token_usage = response.usage
            total_tokens += token_usage.get("input_tokens", 0) + token_usage.get("output_tokens", 0)

            if not response.tool_calls:
                return AgentRunResult(
                    steps=steps,
                    output=response.content,
                    blackboard_changes={"final_state": blackboard.orchestrator_state},
                    status="completed",
                    retry_count=llm_error_count,
                )

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool = next((t for t in config.tools if t.name == tool_name), None)
                if tool is None:
                    malformed_count, abort = _handle_malformed_tool(
                        tool_name, f"Tool call: {tool_name}", config,
                        malformed_count, messages, steps,
                    )
                    if abort is not None:
                        return abort
                    break

                args = tool_call.get("args", {})

                if tool.confirm_before:
                    confirm_id = f"{tool.name}-{step_num}-{uuid4().hex[:8]}"
                    event = asyncio.Event()
                    blackboard._confirm_events[confirm_id] = event
                    blackboard.emit_event({
                        "type": "confirm_request",
                        "id": confirm_id,
                        "tool": tool.name,
                        "args": args,
                        "summary": tool.description,
                    })
                    try:
                        await asyncio.wait_for(event.wait(), timeout=blackboard.autonomy_config.confirm_timeout_s)  # noqa: E501
                    except TimeoutError:
                        action = blackboard.autonomy_config.timeout_action
                        if action == "skip":
                            continue
                        elif action == "abort_task":
                            return AgentRunResult(
                                steps=steps, output="", blackboard_changes={},
                                status="cancelled", retry_count=llm_error_count,
                            )
                        elif action == "downgrade_and_continue":
                            pass
                        else:
                            continue
                    else:
                        outcome = blackboard._confirm_outcomes.get(confirm_id)
                        if outcome:
                            if outcome.get("action") == "reject":
                                continue
                            elif outcome.get("action") == "modify":
                                args = outcome.get("modification", args)

                _execute_tool_step(
                    tool, args, response.content or "", f"Called {tool.name}",
                    step_num, blackboard, messages, steps, token_usage,
                )

            continue

        # JSON fallback path
        if "Available tools:" not in messages[0]["content"]:
            tool_schema_desc = _build_tool_schema_description(config.tools)
            messages[0]["content"] += (
                "\n\nYou MUST respond with valid JSON exactly matching one of these formats:\n"
                '{"thought": "<reasoning>", "tool": "<tool_name>", "args": {...}}\n'
                '{"action": "finish", "summary": "<final summary>"}\n'
                '{"action": "handoff", "summary": "<handoff summary>"}\n\n'
                f"Available tools:\n{tool_schema_desc}"
            )

        try:
            t0 = time.monotonic()
            json_response: LLMResponse = await adapter.generate(
                messages, temperature=config.temperature,
            )
            _try_record_usage(json_response.usage, int((time.monotonic() - t0) * 1000))
        except Exception as e:
            llm_error_count, abort = await _handle_llm_error(llm_error_count, e, steps)
            if abort is not None:
                return abort
            continue

        token_usage = json_response.usage
        total_tokens += token_usage.get("input_tokens", 0) + token_usage.get("output_tokens", 0)

        try:
            parsed = json.loads(json_response.content)
        except json.JSONDecodeError:
            malformed_count += 1
            if malformed_count > 2:
                return AgentRunResult(
                    steps=steps, output="", blackboard_changes={},
                    status="error", error_code="malformed_response",
                    retry_count=malformed_count,
                )
            messages.append({"role": "assistant", "content": json_response.content})
            messages.append({"role": "system", "content": "上一轮输出不是有效 JSON，请用 JSON 格式重新输出。"})  # noqa: E501
            continue

        if "action" in parsed and parsed["action"] == "finish":
            return AgentRunResult(
                steps=steps,
                output=parsed.get("summary", ""),
                blackboard_changes={"final_state": blackboard.orchestrator_state},
                status="completed",
                retry_count=llm_error_count,
            )

        if "action" in parsed and parsed["action"] == "handoff":
            return AgentRunResult(
                steps=steps,
                output=parsed.get("summary", ""),
                blackboard_changes={},
                status="handoff",
                retry_count=llm_error_count,
            )

        if "tool" in parsed:
            tool_name = parsed["tool"]
            tool = next((t for t in config.tools if t.name == tool_name), None)
            if tool is None:
                malformed_count, abort = _handle_malformed_tool(
                    tool_name, json_response.content, config,
                    malformed_count, messages, steps,
                )
                if abort is not None:
                    return abort
                continue

            args = parsed.get("args", {})
            _execute_tool_step(
                tool, args, parsed.get("thought", ""), json_response.content,
                step_num, blackboard, messages, steps, token_usage,
            )

    messages.append({"role": "system", "content": "已达到最大步数限制，请给出 finish。"})
    try:
        t0 = time.monotonic()
        response = await adapter.generate(messages, temperature=config.temperature)
        _try_record_usage(response.usage, int((time.monotonic() - t0) * 1000))
        parsed = json.loads(response.content)
        return AgentRunResult(
            steps=steps, output=parsed.get("summary", "Max steps reached, no summary"),
            blackboard_changes={}, status="max_steps_reached",
        )
    except Exception:
        return AgentRunResult(
            steps=steps, output="", blackboard_changes={},
            status="max_steps_reached",
        )


def _build_tool_schema_description(tools: list[Tool]) -> str:
    lines = []
    for t in tools:
        params_desc = json.dumps(t.parameters, ensure_ascii=False) if t.parameters else "{}"
        lines.append(f"- {t.name}: {t.description} | parameters: {params_desc}")
    return "\n".join(lines)


def _execute_tool_step(
    tool: Tool,
    args: dict[str, Any],
    thought: str,
    assistant_content: str,
    step_num: int,
    blackboard: BlackboardProtocol,
    messages: list[dict[str, str]],
    steps: list[AgentStep],
    token_usage: dict[str, int],
) -> None:
    try:
        tool_result = tool.handler(**args)
    except Exception as e:
        tool_result = f"Tool execution error: {e}"
    result_str = str(tool_result)[:2000]
    step = AgentStep(
        thought=thought,
        tool_name=tool.name,
        tool_args=args,
        result=result_str,
        token_usage=token_usage,
    )
    steps.append(step)
    blackboard.record_step(step)
    messages.append({"role": "assistant", "content": assistant_content})
    messages.append({"role": "system", "content": f"工具 '{tool.name}' 执行结果：\n{result_str}"})
    blackboard.emit_event({
        "type": "tool_call", "agent": "agent", "tool": tool.name,
        "args": args, "sequence": step_num,
    })
    blackboard.emit_event({
        "type": "tool_result", "agent": "agent", "tool": tool.name,
        "result": str(tool_result)[:500], "summary": str(tool_result)[:200],
        "sequence": step_num,
    })
    if step_num % 5 == 0:
        blackboard.emit_event({"type": "checkpoint", "step": step_num, "sequence": step_num})


async def _handle_llm_error(
    llm_error_count: int, error: Exception, steps: list[AgentStep],
) -> tuple[int, AgentRunResult | None]:
    new_count = llm_error_count + 1
    if new_count > RETRY_POLICY["llm_unavailable"]["max_retries"]:
        return new_count, AgentRunResult(
            steps=steps, output="", blackboard_changes={},
            status="error", error_code="llm_unavailable",
            retry_count=new_count,
        )
    logger.warning(f"LLM call failed (attempt {new_count}): {error}")
    await asyncio.sleep(2 ** min(new_count, 5))
    return new_count, None


def _handle_malformed_tool(
    tool_name: str,
    assistant_content: str,
    config: AgentConfig,
    malformed_count: int,
    messages: list[dict[str, str]],
    steps: list[AgentStep],
) -> tuple[int, AgentRunResult | None]:
    new_count = malformed_count + 1
    if new_count > 2:
        return new_count, AgentRunResult(
            steps=steps, output="", blackboard_changes={},
            status="error", error_code="malformed_response",
        )
    available = ", ".join(t.name for t in config.tools)
    messages.append({"role": "assistant", "content": assistant_content})
    messages.append({
        "role": "system",
        "content": f"工具 '{tool_name}' 不存在。可用工具：{available}。请重新选择。",
    })
    return new_count, None


# Error code → retry policy mapping
RETRY_POLICY: dict[str, dict[str, Any]] = {
    "llm_unavailable": {"max_retries": 3, "backoff": "exponential"},
    "malformed_response": {"max_retries": 2, "backoff": "immediate"},
}

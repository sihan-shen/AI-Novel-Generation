"""Agent base classes: AgentConfig, Tool, AgentStep, AgentRunResult."""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AgentConfig:
    system_prompt: str
    tools: list["Tool"]
    model: str
    temperature: float = 0.7
    max_steps: int = 15
    token_budget: int = 100_000


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., str]
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
    status: str  # completed | max_steps_reached | budget_exceeded | error
    error_code: str | None = None
    retry_count: int = 0


import json
import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_agent(
    config: AgentConfig,
    blackboard: "Blackboard",
    adapter: Any,
) -> AgentRunResult:
    """Execute the agent tool-calling loop against the given blackboard."""
    from app.llm.adapter import LLMResponse

    messages = [
        {"role": "system", "content": config.system_prompt},
        {"role": "user", "content": blackboard.get_context_for("agent")},
    ]

    tool_schema_desc = _build_tool_schema_description(config.tools)
    messages[0]["content"] += (
        "\n\nYou MUST respond with valid JSON exactly matching one of these formats:\n"
        f'{{"thought": "<reasoning>", "tool": "<tool_name>", "args": {{...}}}}\n'
        f'{{"action": "finish", "summary": "<final summary>"}}\n'
        f'{{"action": "handoff", "summary": "<handoff summary>"}}\n\n'
        f"Available tools:\n{tool_schema_desc}"
    )

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

        try:
            response: LLMResponse = await adapter.generate(messages, temperature=config.temperature)
        except Exception as e:
            llm_error_count += 1
            if llm_error_count > RETRY_POLICY["llm_unavailable"]["max_retries"]:
                return AgentRunResult(
                    steps=steps, output="", blackboard_changes={},
                    status="error", error_code="llm_unavailable",
                    retry_count=llm_error_count,
                )
            logger.warning(f"LLM call failed (attempt {llm_error_count}): {e}")
            await asyncio.sleep(2 ** min(llm_error_count, 5))
            continue

        token_usage = response.usage
        total_tokens += token_usage.get("input_tokens", 0) + token_usage.get("output_tokens", 0)

        try:
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            malformed_count += 1
            if malformed_count > 2:
                return AgentRunResult(
                    steps=steps, output="", blackboard_changes={},
                    status="error", error_code="malformed_response",
                    retry_count=malformed_count,
                )
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "system", "content": "上一轮输出不是有效 JSON，请用 JSON 格式重新输出。"})
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
                malformed_count += 1
                if malformed_count > 2:
                    return AgentRunResult(
                        steps=steps, output="", blackboard_changes={},
                        status="error", error_code="malformed_response",
                    )
                available = ", ".join(t.name for t in config.tools)
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "system", "content": f"工具 '{tool_name}' 不存在。可用工具：{available}。请重新选择。"})
                continue

            args = parsed.get("args", {})
            try:
                tool_result = tool.handler(**args)
            except Exception as e:
                tool_result = f"Tool execution error: {e}"

            step = AgentStep(
                thought=parsed.get("thought", ""),
                tool_name=tool_name,
                tool_args=args,
                result=str(tool_result)[:2000],
                token_usage=token_usage,
            )
            steps.append(step)
            blackboard.record_step(step)

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "system", "content": f"工具 '{tool_name}' 执行结果：\n{str(tool_result)[:2000]}"})

            blackboard.emit_event({"type": "tool_call", "agent": "agent", "tool": tool_name, "args": args, "sequence": step_num})
            blackboard.emit_event({"type": "tool_result", "agent": "agent", "tool": tool_name, "result": str(tool_result)[:500], "summary": str(tool_result)[:200], "sequence": step_num})

            if step_num % 5 == 0:
                blackboard.emit_event({"type": "checkpoint", "step": step_num, "sequence": step_num})

    messages.append({"role": "system", "content": "已达到最大步数限制，请给出 finish。"})
    try:
        response = await adapter.generate(messages, temperature=config.temperature)
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


# Error code → retry policy mapping
RETRY_POLICY: dict[str, dict[str, Any]] = {
    "llm_unavailable": {"max_retries": 3, "backoff": "exponential"},
    "tool_timeout": {"max_retries": 2, "backoff": "exponential"},
    "rate_limited": {"max_retries": 5, "backoff": "exponential"},
    "db_error": {"max_retries": 0, "backoff": None},
    "malformed_response": {"max_retries": 2, "backoff": "immediate"},
    "budget_exceeded": {"max_retries": 0, "backoff": None},
}

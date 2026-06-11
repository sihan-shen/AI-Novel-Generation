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


# Error code → retry policy mapping
RETRY_POLICY: dict[str, dict[str, Any]] = {
    "llm_unavailable": {"max_retries": 3, "backoff": "exponential"},
    "tool_timeout": {"max_retries": 2, "backoff": "exponential"},
    "rate_limited": {"max_retries": 5, "backoff": "exponential"},
    "db_error": {"max_retries": 0, "backoff": None},
    "malformed_response": {"max_retries": 2, "backoff": "immediate"},
    "budget_exceeded": {"max_retries": 0, "backoff": None},
}

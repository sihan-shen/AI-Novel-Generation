"""Protocol types for core agent abstractions — enables static type checking
without introducing runtime coupling.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BlackboardProtocol(Protocol):
    """Protocol for the shared Blackboard used by agents and orchestrator."""

    project_id: str
    orchestrator_state: str
    current_chapter_id: str | None
    cumulative_tokens: int
    token_budget: int
    current_draft: str | None
    is_rewrite: bool
    rewrite_round: int
    last_review: dict | None
    pending_setting_changes: list
    autonomy_config: Any  # AutonomyConfig — avoid circular import
    events: Any  # asyncio.Queue
    _settings_context: str
    _confirm_events: dict
    _confirm_outcomes: dict
    task: dict

    def emit_event(self, event: dict) -> None: ...
    def get_context_for(self, agent_type: str) -> str: ...
    def record_step(self, step: Any) -> None: ...
    def set_project_context(
        self, meta: dict, settings: str, outline: str, style: str
    ) -> None: ...
    def to_snapshot(self) -> dict: ...


@runtime_checkable
class LLMAdapterProtocol(Protocol):
    """Protocol for LLM adapters."""

    supports_native_tools: bool
    model: str

    async def generate(self, messages: list[dict], **kwargs) -> Any: ...
    async def generate_stream(
        self, messages: list[dict], **kwargs
    ) -> AsyncGenerator[str, None]: ...
    def count_tokens(self, text: str) -> int: ...
    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        stream_callback: Any | None,
    ) -> Any: ...

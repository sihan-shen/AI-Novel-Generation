"""Blackboard — shared state for agent coordination with context compression."""

import asyncio
import json
import re
from app.agents.base import AgentStep
from app.agents.autonomy import AutonomyConfig

# Known separators that could break out of prompt structure
_DANGEROUS_PATTERNS = [
    (r'<\|SYSTEM\|>', '[SYSTEM_ESCAPED]'),
    (r'<\|END\|>', '[END_ESCAPED]'),
    (r'</?SYSTEM>', '[SYSTEM_TAG]'),
    (r'</?ASSISTANT>', '[ASSISTANT_TAG]'),
    (r'</?USER>', '[USER_TAG]'),
    (r'\[INST\]', '[INST_TOKEN]'),
    (r'\[/INST\]', '[/INST_TOKEN]'),
]


def _sanitize(text: str) -> str:
    """Sanitize user data before injecting into prompt context.

    Replaces known delimiter patterns with safe ASCII escape sequences
    to prevent prompt injection attacks.
    """
    if not text:
        return text
    for pattern, replacement in _DANGEROUS_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _rough_token_count(text: str) -> int:
    chinese_chars = sum(1 for c in text if '一' <= c <= '鿿')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 0.5 + other_chars / 3.5)


def _compress_steps(steps: list[AgentStep]) -> str:
    if not steps:
        return ""
    lines = [f"[上下文摘要] 步骤 {len(steps)} 条:"]
    for s in steps:
        lines.append(f"  工具={s.tool_name}, 结果={s.result[:100]}...")
    return "\n".join(lines)[:3000]


class Blackboard:
    def __init__(
        self,
        project_id: str,
        task: dict,
        autonomy_config: AutonomyConfig,
    ):
        self.project_id = project_id
        self.task = task
        self.orchestrator_state = "IDLE"
        self.current_chapter_id: str | None = None
        self.current_draft: str | None = None
        self.last_review: dict | None = None
        self.pending_setting_changes: list[dict] = []
        self.agent_steps: list[AgentStep] = []
        self.rewrite_round: int = 0
        self.autonomy_config = autonomy_config
        self.events: asyncio.Queue = asyncio.Queue()
        self.cumulative_tokens: int = 0
        self.compression_tokens: int = 0
        self.token_budget: int = autonomy_config.token_budget
        self.context_summaries: list[str] = []
        self._compression_threshold = 30_000
        self._work_layer_size = 5
        self._project_meta: dict = {}
        self._settings_context: str = ""
        self._outline_context: str = ""
        self._style_context: str = ""

    def set_project_context(self, meta: dict, settings: str, outline: str, style: str) -> None:
        self._project_meta = meta
        self._settings_context = _sanitize(settings)
        self._outline_context = _sanitize(outline)
        self._style_context = _sanitize(style)

    def get_context_for(self, agent_type: str) -> str:
        parts = [f"=== 项目信息 ===\n项目ID: {self.project_id}\n状态: {self.orchestrator_state}"]
        if self._project_meta:
            parts.append(f"类型: {self._project_meta.get('genre', '')}")
            parts.append(f"状态: {self._project_meta.get('status', '')}")
        if self._settings_context:
            parts.append(f"\n=== 设定集 ===\n{self._settings_context}")
        if self._outline_context:
            parts.append(f"\n=== 大纲 ===\n{self._outline_context}")
        if self._style_context:
            parts.append(f"\n=== 文风 ===\n{self._style_context}")

        if self.agent_steps:
            recent = self.agent_steps[-self._work_layer_size:]
            parts.append("\n=== 最近操作 ===")
            for i, s in enumerate(recent):
                parts.append(f"{i+1}. {s.thought}")
                if s.tool_name:
                    parts.append(f"   工具: {s.tool_name}({s.tool_args})")
                    parts.append(f"   结果: {s.result[:300]}")

        old_steps = self.agent_steps[:-self._work_layer_size]
        if old_steps:
            parts.append("\n=== 历史摘要 ===")
            parts.append(_compress_steps(old_steps))

        return "\n".join(parts)

    def write_draft(self, content: str) -> None:
        self.current_draft = content

    def record_step(self, step: AgentStep) -> None:
        self.agent_steps.append(step)
        tokens = step.token_usage.get("input_tokens", 0) + step.token_usage.get("output_tokens", 0)
        self.cumulative_tokens += tokens

    def emit_event(self, event: dict) -> None:
        self.events.put_nowait(event)

    def to_snapshot(self) -> dict:
        return {
            "project_id": self.project_id,
            "task": self.task,
            "orchestrator_state": self.orchestrator_state,
            "current_chapter_id": self.current_chapter_id,
            "current_draft": self.current_draft,
            "last_review": self.last_review,
            "pending_setting_changes": self.pending_setting_changes,
            "agent_steps": [{"thought": s.thought, "tool_name": s.tool_name, "tool_args": s.tool_args, "result": s.result, "token_usage": s.token_usage} for s in self.agent_steps],
            "rewrite_round": self.rewrite_round,
            "autonomy_config": self.autonomy_config.to_dict(),
            "cumulative_tokens": self.cumulative_tokens,
            "compression_tokens": self.compression_tokens,
            "token_budget": self.token_budget,
            "context_summaries": self.context_summaries,
        }

    @classmethod
    def from_snapshot(cls, data: dict) -> "Blackboard":
        bb = cls(
            project_id=data["project_id"],
            task=data["task"],
            autonomy_config=AutonomyConfig.from_dict(data["autonomy_config"]),
        )
        bb.orchestrator_state = data["orchestrator_state"]
        bb.current_chapter_id = data.get("current_chapter_id")
        bb.current_draft = data.get("current_draft")
        bb.last_review = data.get("last_review")
        bb.pending_setting_changes = data.get("pending_setting_changes", [])
        bb.agent_steps = [AgentStep(thought=s["thought"], tool_name=s["tool_name"], tool_args=s["tool_args"], result=s["result"], token_usage=s["token_usage"]) for s in data.get("agent_steps", [])]
        bb.rewrite_round = data.get("rewrite_round", 0)
        bb.cumulative_tokens = data.get("cumulative_tokens", 0)
        bb.compression_tokens = data.get("compression_tokens", 0)
        bb.token_budget = data.get("token_budget", 100_000)
        bb.context_summaries = data.get("context_summaries", [])
        return bb

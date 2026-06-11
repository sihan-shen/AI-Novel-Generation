"""Orchestrator — state machine that coordinates agent execution."""

from enum import Enum
import logging
from app.agents.blackboard import Blackboard

logger = logging.getLogger(__name__)


class OrchestratorState(str, Enum):
    IDLE = "IDLE"
    GATHERING_CONTEXT = "GATHERING_CONTEXT"
    WRITING = "WRITING"
    REVIEWING = "REVIEWING"
    FIXING_SETTINGS = "FIXING_SETTINGS"
    REWRITING = "REWRITING"
    WAITING_USER = "WAITING_USER"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class Orchestrator:
    def __init__(self, db, blackboard: Blackboard, adapter):
        self.db = db
        self.blackboard = blackboard
        self.adapter = adapter
        self.state = OrchestratorState.IDLE
        self._project_id = blackboard.project_id

    async def run(self) -> OrchestratorState:
        self.state = OrchestratorState.GATHERING_CONTEXT
        while self.state not in (OrchestratorState.IDLE, OrchestratorState.DONE, OrchestratorState.CANCELLED):
            self.blackboard.orchestrator_state = self.state.value
            if self.state == OrchestratorState.GATHERING_CONTEXT:
                self.state = self._gathering_context()
            elif self.state == OrchestratorState.WRITING:
                self.state = await self._run_writer()
            elif self.state == OrchestratorState.REVIEWING:
                self.state = OrchestratorState.DONE
            elif self.state == OrchestratorState.DONE:
                self.state = self._done()
            elif self.state == OrchestratorState.WAITING_USER:
                break
            else:
                self.state = OrchestratorState.IDLE
        self.blackboard.orchestrator_state = self.state.value
        return self.state

    def _gathering_context(self) -> OrchestratorState:
        self.blackboard.emit_event({"type": "orchestrator_thought", "text": "正在收集设定和大纲上下文...", "step": 0, "sequence": 0})
        try:
            from app.services.project_service import ProjectService
            project = ProjectService.get(self.db, self._project_id)
            if project:
                self.blackboard.set_project_context(meta={"genre": project.genre, "status": project.status}, settings="", outline="", style="")
            from app.services.setting_service import SettingService
            settings_context = SettingService.build_llm_context(self.db, self._project_id)
            self.blackboard._settings_context = settings_context
        except Exception as e:
            logger.error(f"GATHERING_CONTEXT failed: {e}")
            self.blackboard.emit_event({"type": "error", "message": f"上下文收集失败: {e}"})
            return OrchestratorState.IDLE
        return OrchestratorState.WRITING

    async def _run_writer(self) -> OrchestratorState:
        from app.agents.base import run_agent
        from app.agents.agents.writer import build_writer_config
        self.blackboard.emit_event({"type": "agent_start", "agent": "writer", "task": self.blackboard.task.get("chapter_outline_id", ""), "sequence": 1})
        config = build_writer_config(db=self.db, project_id=self._project_id, blackboard=self.blackboard, write_mode=self.blackboard.autonomy_config.write_mode)
        result = await run_agent(config, self.blackboard, self.adapter)
        if self.blackboard.current_draft:
            self.blackboard.emit_event({"type": "agent_output", "agent": "writer", "type": "chapter_draft", "preview": self.blackboard.current_draft[:200], "sequence": 99})
        return OrchestratorState.DONE

    def _done(self) -> OrchestratorState:
        self.blackboard.emit_event({"type": "task_complete", "task_id": "", "summary": "写作任务完成", "sequence": 999})
        return OrchestratorState.IDLE

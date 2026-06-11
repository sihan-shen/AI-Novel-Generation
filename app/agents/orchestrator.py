"""Orchestrator — full state machine with WRITING→REVIEWING→FIXING_SETTINGS→REWRITING loop."""

import json
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
    def __init__(self, db, blackboard: Blackboard, adapter, task_id: str | None = None):
        self.db = db
        self.blackboard = blackboard
        self.adapter = adapter
        self.state = OrchestratorState.IDLE
        self._project_id = blackboard.project_id
        self._task_id = task_id

    async def run(self) -> OrchestratorState:
        logger.info(f"Orchestrator started for project {self._project_id}", extra={"state": "start", "project_id": self._project_id})
        self.state = OrchestratorState.GATHERING_CONTEXT
        while self.state not in (OrchestratorState.IDLE, OrchestratorState.DONE, OrchestratorState.CANCELLED):
            self.blackboard.orchestrator_state = self.state.value
            if self.state == OrchestratorState.GATHERING_CONTEXT:
                self.state = self._gathering_context()
            elif self.state == OrchestratorState.WRITING:
                self.state = await self._run_writer()
            elif self.state == OrchestratorState.REVIEWING:
                self.state = await self._run_reviewer()
            elif self.state == OrchestratorState.FIXING_SETTINGS:
                self.state = await self._run_settings_mgr()
            elif self.state == OrchestratorState.REWRITING:
                self.state = await self._run_rewriter()
            elif self.state == OrchestratorState.DONE:
                self.state = self._done()
            elif self.state == OrchestratorState.WAITING_USER:
                break
            else:
                self.state = OrchestratorState.IDLE
        self.blackboard.orchestrator_state = self.state.value
        logger.info(f"Orchestrator finished: {self.state.value}", extra={"state": "end", "project_id": self._project_id, "final_state": self.state.value})
        return self.state

    def _gathering_context(self) -> OrchestratorState:
        logger.info("orchestrator.state", extra={"state": self.state.value, "project_id": self._project_id})
        self.blackboard.emit_event({"type": "orchestrator_thought", "text": "正在收集设定和大纲上下文...", "step": 0, "sequence": 0})
        try:
            from app.services.project_service import ProjectService
            project = ProjectService.get(self.db, self._project_id)
            if not project:
                self.blackboard.emit_event({"type": "error", "message": "项目不存在或已被删除", "sequence": 1})
                return OrchestratorState.IDLE
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
        logger.info("orchestrator.state", extra={"state": self.state.value, "project_id": self._project_id})
        from app.agents.base import run_agent
        from app.agents.agents.writer import build_writer_config
        self.blackboard.emit_event({"type": "agent_start", "agent": "writer", "task": self.blackboard.task.get("chapter_outline_id", ""), "sequence": 1})
        config = build_writer_config(db=self.db, project_id=self._project_id, blackboard=self.blackboard, write_mode=self.blackboard.autonomy_config.write_mode, task_id=self._task_id)
        result = await run_agent(config, self.blackboard, self.adapter)
        if self.blackboard.current_draft:
            self.blackboard.emit_event({"type": "agent_output", "agent": "writer", "type": "chapter_draft", "preview": self.blackboard.current_draft[:200], "sequence": 99})
        return OrchestratorState.REVIEWING

    async def _run_reviewer(self) -> OrchestratorState:
        logger.info("orchestrator.state", extra={"state": self.state.value, "project_id": self._project_id})
        from app.agents.base import run_agent
        from app.agents.agents.reviewer import build_reviewer_config
        chapter_id = self.blackboard.current_chapter_id
        if not chapter_id:
            return OrchestratorState.DONE
        self.blackboard.emit_event({"type": "agent_start", "agent": "reviewer", "task": chapter_id, "sequence": 100})
        config = build_reviewer_config(db=self.db, project_id=self._project_id, chapter_id=chapter_id, blackboard=self.blackboard, write_mode=self.blackboard.autonomy_config.write_mode, task_id=self._task_id)
        result = await run_agent(config, self.blackboard, self.adapter)
        overall = 5.0
        try:
            review_dict = json.loads(result.output) if result.output else {}
            overall = review_dict.get("overall_score", 5.0)
        except (json.JSONDecodeError, TypeError):
            pass
        self.blackboard.last_review = {"overall_score": overall}
        self.blackboard.emit_event({"type": "agent_output", "agent": "reviewer", "type": "review_result", "data": {"overall_score": overall}, "sequence": 110})
        if overall < 2.5 and self.blackboard.rewrite_round < self.blackboard.autonomy_config.max_rewrite_rounds:
            self.blackboard.rewrite_round += 1
            self.blackboard.emit_event({"type": "orchestrator_thought", "text": f"审阅分数{overall}，低于阈值2.5，进入第{self.blackboard.rewrite_round}轮重写", "sequence": 111})
            return OrchestratorState.REWRITING
        elif overall < 2.5:
            self.blackboard.emit_event({"type": "orchestrator_thought", "text": f"审阅分数{overall}，已达最大重写轮次，进入人工决策", "sequence": 112})
            return OrchestratorState.WAITING_USER
        if self.blackboard.pending_setting_changes:
            return OrchestratorState.FIXING_SETTINGS
        return OrchestratorState.DONE

    async def _run_settings_mgr(self) -> OrchestratorState:
        from app.agents.base import run_agent
        from app.agents.agents.settings_mgr import build_settings_mgr_config
        self.blackboard.emit_event({"type": "agent_start", "agent": "settings_mgr", "task": "", "sequence": 200})
        config = build_settings_mgr_config(db=self.db, project_id=self._project_id, blackboard=self.blackboard, write_mode=self.blackboard.autonomy_config.write_mode, task_id=self._task_id)
        result = await run_agent(config, self.blackboard, self.adapter)
        return OrchestratorState.REWRITING

    async def _run_rewriter(self) -> OrchestratorState:
        return await self._run_writer()

    def _done(self) -> OrchestratorState:
        logger.info("orchestrator.state", extra={"state": self.state.value, "project_id": self._project_id})
        self.blackboard.emit_event({"type": "task_complete", "task_id": self._task_id or "", "summary": "写作任务完成", "sequence": 999})
        return OrchestratorState.IDLE

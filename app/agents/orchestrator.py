"""Orchestrator — full state machine with WRITING→REVIEWING→FIXING_SETTINGS→REWRITING loop."""

import json
import logging
from enum import StrEnum

from app.agents.blackboard import Blackboard

logger = logging.getLogger(__name__)


class OrchestratorState(StrEnum):
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
        """Caller owns `db` and is responsible for closing it."""
        self.db = db
        self.blackboard = blackboard
        self.adapter = adapter
        self.state = OrchestratorState.IDLE
        self._project_id = blackboard.project_id
        self._task_id = task_id
        self.cancelled: bool = False
        self.milestone_progress: dict = {"current_index": 0, "total": 0, "completed_ids": []}

    def cancel(self) -> None:
        self.cancelled = True

    async def _run_milestone_loop(self) -> OrchestratorState:
        """Iterate over outline nodes at the configured granularity level,
        running the full WRITING→REVIEWING→... sub-loop for each node.
        """
        granularity = self.blackboard.autonomy_config.milestone_granularity
        target_level = 1 if granularity in ("volume", "act") else 2

        from app.services.outline_service import OutlineService
        outline_items = OutlineService.get_tree(self.db, self._project_id)
        milestone_nodes = [n for n in outline_items if n.level == target_level]

        self.milestone_progress["total"] = len(milestone_nodes)

        for node in milestone_nodes:
            if self.cancelled:
                return OrchestratorState.CANCELLED
            if self.blackboard.cumulative_tokens > self.blackboard.token_budget:
                break

            self.milestone_progress["current_index"] += 1
            self.blackboard.current_chapter_id = node.id  # type: ignore[assignment]
            self.blackboard.rewrite_round = 0

            sub_state = OrchestratorState.WRITING
            while sub_state not in (
                OrchestratorState.DONE,
                OrchestratorState.WAITING_USER,
                OrchestratorState.CANCELLED,
            ):
                if self.cancelled:
                    return OrchestratorState.CANCELLED
                if self.blackboard.cumulative_tokens > self.blackboard.token_budget:
                    break
                self.blackboard.orchestrator_state = sub_state.value
                if sub_state == OrchestratorState.WRITING:
                    sub_state = await self._run_writer()
                elif sub_state == OrchestratorState.REVIEWING:
                    sub_state = await self._run_reviewer()
                elif sub_state == OrchestratorState.FIXING_SETTINGS:
                    sub_state = await self._run_settings_mgr()
                elif sub_state == OrchestratorState.REWRITING:
                    sub_state = await self._run_rewriter()
                else:
                    sub_state = OrchestratorState.DONE

            self.milestone_progress["completed_ids"].append(node.id)

            if sub_state == OrchestratorState.WAITING_USER:
                return sub_state

        return OrchestratorState.DONE

    async def run(self) -> OrchestratorState:
        logger.info(f"Orchestrator started for project {self._project_id}", extra={"state": "start", "project_id": self._project_id, "task_id": self._task_id})  # noqa: E501
        self.state = OrchestratorState.GATHERING_CONTEXT
        while self.state not in (OrchestratorState.IDLE, OrchestratorState.DONE, OrchestratorState.CANCELLED):  # noqa: E501
            if self.cancelled:
                self.blackboard.emit_event({"type": "cancelled", "sequence": 0})
                self.state = OrchestratorState.CANCELLED
                break
            self.blackboard.orchestrator_state = self.state.value
            if self.state == OrchestratorState.GATHERING_CONTEXT:
                self.state = self._gathering_context()
            elif self.state == OrchestratorState.WRITING:
                if self.blackboard.autonomy_config.milestone_granularity in ("volume", "act"):
                    self.state = await self._run_milestone_loop()
                else:
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
        logger.info(f"Orchestrator finished: {self.state.value}", extra={"state": "end", "project_id": self._project_id, "final_state": self.state.value})  # noqa: E501
        return self.state

    def _gathering_context(self) -> OrchestratorState:
        logger.info("orchestrator.state", extra={"state": self.state.value, "project_id": self._project_id})  # noqa: E501
        self.blackboard.emit_event({"type": "orchestrator_thought", "text": "正在收集设定和大纲上下文...", "step": 0, "sequence": 0})  # noqa: E501
        try:
            from app.services.project_service import ProjectService
            project = ProjectService.get(self.db, self._project_id)
            if not project:
                self.blackboard.emit_event({"type": "error", "message": "项目不存在或已被删除", "sequence": 1})  # noqa: E501
                return OrchestratorState.IDLE

            import json

            from app.models.style import ProjectStyleLink
            from app.services.outline_service import OutlineService
            from app.services.style_service import StyleService

            outline_items = OutlineService.get_tree(self.db, self._project_id)
            outline_context = json.dumps([
                {"id": i.id, "parent_id": i.parent_id, "level": i.level, "sort_order": i.sort_order, "title": i.title, "summary": i.summary or "", "status": i.status}  # noqa: E501
                for i in outline_items
            ], ensure_ascii=False)

            style_links = self.db.query(ProjectStyleLink).filter(ProjectStyleLink.project_id == self._project_id).all()  # noqa: E501
            styles = []
            for link in style_links:
                style = StyleService.get(self.db, link.style_id)
                if style:
                    styles.append({"name": style.name, "analysis": style.analysis or "{}", "weight": link.weight})  # noqa: E501
            style_context = json.dumps(styles, ensure_ascii=False)

            self.blackboard.set_project_context(
                meta={"genre": project.genre, "status": project.status},
                settings="",
                outline=outline_context,
                style=style_context,
            )
            from app.services.setting_service import SettingService
            settings_context = SettingService.build_llm_context(self.db, self._project_id)
            self.blackboard._settings_context = settings_context
        except Exception as e:
            logger.error(f"GATHERING_CONTEXT failed: {e}")
            self.blackboard.emit_event({"type": "error", "message": f"上下文收集失败: {e}"})
            return OrchestratorState.IDLE
        return OrchestratorState.WRITING

    async def _run_writer(self) -> OrchestratorState:
        logger.info("orchestrator.state", extra={"state": self.state.value, "project_id": self._project_id})  # noqa: E501
        from app.agents.agents.writer import build_writer_config
        from app.agents.base import run_agent
        self.blackboard.emit_event({"type": "agent_start", "agent": "writer", "task": self.blackboard.task.get("chapter_outline_id", ""), "sequence": 1})  # noqa: E501
        config = build_writer_config(db=self.db, project_id=self._project_id, blackboard=self.blackboard, write_mode=self.blackboard.autonomy_config.write_mode, task_id=self._task_id)  # noqa: E501
        _ = await run_agent(config, self.blackboard, self.adapter, db=self.db, agent_type="writer")  # noqa: E501
        if self.blackboard.current_draft:
            self.blackboard.emit_event({"type": "agent_output", "agent": "writer", "output_type": "chapter_draft", "preview": self.blackboard.current_draft[:200], "sequence": 99})  # noqa: E501
        return OrchestratorState.REVIEWING

    async def _run_reviewer(self) -> OrchestratorState:
        logger.info("orchestrator.state", extra={"state": self.state.value, "project_id": self._project_id})  # noqa: E501
        from app.agents.agents.reviewer import build_reviewer_config
        from app.agents.base import run_agent
        chapter_id = self.blackboard.current_chapter_id
        if not chapter_id:
            return OrchestratorState.DONE
        self.blackboard.emit_event({"type": "agent_start", "agent": "reviewer", "task": chapter_id, "sequence": 100})  # noqa: E501
        config = build_reviewer_config(db=self.db, project_id=self._project_id, chapter_id=chapter_id, blackboard=self.blackboard, write_mode=self.blackboard.autonomy_config.write_mode, task_id=self._task_id)  # noqa: E501
        review_result = await run_agent(config, self.blackboard, self.adapter, db=self.db, agent_type="reviewer")  # noqa: E501
        overall = 5.0
        try:
            review_dict = json.loads(review_result.output) if review_result.output else {}
            overall = review_dict.get("overall_score", 5.0)
        except (json.JSONDecodeError, TypeError):
            pass
        self.blackboard.last_review = {"overall_score": overall}
        self.blackboard.emit_event({"type": "agent_output", "agent": "reviewer", "output_type": "review_result", "data": {"overall_score": overall}, "sequence": 110})  # noqa: E501
        if overall < 2.5 and self.blackboard.rewrite_round < self.blackboard.autonomy_config.max_rewrite_rounds:  # noqa: E501
            self.blackboard.rewrite_round += 1
            self.blackboard.emit_event({"type": "orchestrator_thought", "text": f"审阅分数{overall}，低于阈值2.5，进入第{self.blackboard.rewrite_round}轮重写", "sequence": 111})  # noqa: E501
            return OrchestratorState.REWRITING
        elif overall < 2.5:
            self.blackboard.emit_event({"type": "orchestrator_thought", "text": f"审阅分数{overall}，已达最大重写轮次，进入人工决策", "sequence": 112})  # noqa: E501
            return OrchestratorState.WAITING_USER
        if self.blackboard.pending_setting_changes:
            return OrchestratorState.FIXING_SETTINGS
        return OrchestratorState.DONE

    async def _run_settings_mgr(self) -> OrchestratorState:
        from app.agents.agents.settings_mgr import build_settings_mgr_config
        from app.agents.base import run_agent
        self.blackboard.emit_event({"type": "agent_start", "agent": "settings_mgr", "task": "", "sequence": 200})  # noqa: E501
        config = build_settings_mgr_config(db=self.db, project_id=self._project_id, blackboard=self.blackboard, write_mode=self.blackboard.autonomy_config.write_mode, task_id=self._task_id)  # noqa: E501
        _ = await run_agent(config, self.blackboard, self.adapter, db=self.db, agent_type="settings_mgr")  # noqa: E501
        return OrchestratorState.REWRITING

    async def _run_rewriter(self) -> OrchestratorState:
        self.blackboard.is_rewrite = True
        try:
            return await self._run_writer()
        finally:
            self.blackboard.is_rewrite = False

    def _done(self) -> OrchestratorState:
        logger.info("orchestrator.state", extra={"state": self.state.value, "project_id": self._project_id, "task_id": self._task_id})  # noqa: E501
        self.blackboard.emit_event({"type": "task_complete", "task_id": self._task_id or "", "summary": "写作任务完成", "sequence": 999})  # noqa: E501
        return OrchestratorState.IDLE

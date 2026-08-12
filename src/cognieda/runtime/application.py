from __future__ import annotations

from sqlmodel import Session

from cognieda.agents.planner.agent import Planner
from cognieda.application.ports import AgentFactoryPort
from cognieda.application.services import ActivePlanExecutor, commit_approved_plan
from cognieda.execution import ExecutorDispatcher
from cognieda.schemas import PlanDraft, PlanDraftApproval, PlanDraftDecision
from cognieda.schemas.artifacts import SessionFrame

from .conversation import ConversationHistory
from .messages import Message, MessageRole, MessageType
from .planner_context import apply_planner_output, build_planning_context
from .workspace import Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        dispatcher: ExecutorDispatcher,
        agent_factory: AgentFactoryPort,
        session: Session | None = None,
    ) -> None:
        self.workspace = workspace
        self.agent_factory = agent_factory
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher
        self.session = session
        self.session_frame = SessionFrame()
        self.conversation_history = ConversationHistory()
        self.pending_plan_draft: PlanDraft | None = None

    async def submit_message(self, message: str) -> Message:
        if message.startswith("/"):
            return await self._handle_command(message)

        planning_context = build_planning_context(
            self.session_frame,
            self.conversation_history,
        )
        planner_output = await self.planner_agent.run(
            message,
            planning_context=planning_context,
        )
        self.session_frame = apply_planner_output(self.session_frame, planner_output)
        if planner_output.plan_draft is not None:
            self.pending_plan_draft = planner_output.plan_draft
        if planner_output.new_messages:
            self.conversation_history = self.conversation_history.add_turn(
                planner_output.new_messages
            )

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=planner_output.response,
        )

    # TODO: Move command handling to a separate class or module for better separation of concerns
    async def _handle_command(self, command: str) -> Message:
        parts = command.split()

        match parts:
            case ["/approve", fingerprint]:
                return await self._approve_pending_plan(fingerprint)

            case ["/reject", fingerprint]:
                return self._reject_pending_plan(fingerprint)

            #
            # Register a skill in skills.toml
            #
            case ["/skill", "register", name, directory]:
                self.workspace.add_skill(name, directory)
                return self._text(
                    f"Registered skill '{name}' at '{directory}'."
                )

            case ["/skill", "unregister", name]:
                self.workspace.remove_skill(name)
                return self._text(
                    f"Unregistered skill '{name}'."
                )

            #
            # Assign a skill to a worker in agents.toml
            #
            case ["/skill", "assign", worker, skill]:
                self.workspace.add_worker_skill(worker, skill)
                self.agent_factory.reload_tooling()
                await self.planner_agent.reload_model()

                return self._text(
                    f"Assigned skill '{skill}' to '{worker}'."
                )

            case ["/skill", "unassign", worker, skill]:
                self.workspace.remove_worker_skill(worker, skill)
                self.agent_factory.reload_tooling()
                await self.planner_agent.reload_model()

                return self._text(
                    f"Removed skill '{skill}' from '{worker}'."
                )

            case _:
                return self._text(
                    f"Unknown command: '{command}'."
                )

    def _exact_pending_draft(self, fingerprint: str) -> PlanDraft | None:
        draft = self.pending_plan_draft
        if draft is None or draft.fingerprint != fingerprint:
            return None
        return draft

    async def _approve_pending_plan(self, fingerprint: str) -> Message:
        draft = self._exact_pending_draft(fingerprint)
        if draft is None:
            return self._text("Approval did not match the exact pending PlanDraft.")
        if self.session is None:
            return self._text("Authoritative plan persistence is unavailable.")
        data_profile = self.session_frame.data_profile
        if data_profile is None:
            return self._text("Approved DATA execution requires an active DataProfile.")

        committed = commit_approved_plan(
            self.session,
            plan_draft=draft,
            approval=PlanDraftApproval(
                plan_draft_id=draft.plan_draft_id,
                plan_draft_fingerprint=draft.fingerprint,
                decision=PlanDraftDecision.APPROVE,
            ),
        )
        self.pending_plan_draft = None
        successor = self.session_frame.set_objective(committed.objective)
        for task in committed.tasks:
            successor = successor.add_task(task)
        self.session_frame = successor

        executed = await ActivePlanExecutor(self.session, self.dispatcher).execute_next(
            objective_id=committed.objective.objective_id,
            data_profile_id=data_profile.data_profile_id,
        )
        self.session_frame = self.session_frame.set_task_status(
            executed.task.task_id,
            executed.task.status,
        )
        return self._text(self.planner_agent.respond_to_work(executed.planner_outcome))

    def _reject_pending_plan(self, fingerprint: str) -> Message:
        draft = self._exact_pending_draft(fingerprint)
        if draft is None:
            return self._text("Rejection did not match the exact pending PlanDraft.")
        self.pending_plan_draft = None
        return self._text(
            "The exact PlanDraft was rejected. No authoritative Task or PlanRevision was created."
        )

    def _text(self, content: str) -> Message:
        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=content,
        )

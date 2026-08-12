from __future__ import annotations

from sqlmodel import Session

from cognieda.agents.planner.agent import Planner
from cognieda.application.ports import AgentFactoryPort
from cognieda.application.services import ActivePlanExecutor, commit_approved_plan
from cognieda.execution import ExecutorDispatcher
from cognieda.schemas.artifacts import Objective, SessionFrame, Task
from cognieda.schemas.plan_revision import PlanRevision

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
        self._pending_objective: Objective | None = None
        self._pending_tasks: tuple[Task, ...] = ()
        self._pending_plan_revision: PlanRevision | None = None

    async def submit_message(self, message: str) -> Message:
        command_name = message.split(maxsplit=1)[0].casefold() if message.startswith("/") else ""
        if command_name in {"/approve", "/reject", "/skill"}:
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
        if planner_output.proposed_plan_revision is not None:
            if self._pending_plan_revision is not None:
                return self._text(
                    "A plan is already pending Human approval. Use /approve or /reject "
                    "before proposing another plan."
                )
            if planner_output.proposed_objective is None or not planner_output.proposed_tasks:
                return self._text("Planner returned an incomplete transient plan proposal.")
            self._pending_objective = planner_output.proposed_objective
            self._pending_tasks = planner_output.proposed_tasks
            self._pending_plan_revision = planner_output.proposed_plan_revision
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
            case ["/approve"]:
                return await self._approve_pending_plan()

            case ["/reject"]:
                return self._reject_pending_plan()

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

    async def _approve_pending_plan(self) -> Message:
        objective = self._pending_objective
        tasks = self._pending_tasks
        revision = self._pending_plan_revision
        if objective is None or not tasks or revision is None:
            return self._text("No plan is pending Human approval.")
        if self.session is None:
            return self._text("Authoritative plan persistence is unavailable.")
        data_profile = self.session_frame.data_profile
        if data_profile is None:
            return self._text("Approved DATA execution requires an active DataProfile.")

        commit_approved_plan(
            self.session,
            objective=objective,
            tasks=tasks,
            plan_revision=revision,
        )
        self._clear_pending_plan()
        successor = self.session_frame.set_objective(objective)
        for task in tasks:
            successor = successor.add_task(task)
        self.session_frame = successor

        executed = await ActivePlanExecutor(self.session, self.dispatcher).execute_next(
            objective_id=objective.objective_id,
            data_profile_id=data_profile.data_profile_id,
        )
        self.session_frame = self.session_frame.set_task_status(
            executed.task.task_id,
            executed.task.status,
        )
        return self._text(self.planner_agent.respond_to_work(executed.planner_outcome))

    def _reject_pending_plan(self) -> Message:
        if self._pending_plan_revision is None:
            return self._text("No plan is pending Human rejection.")
        self._clear_pending_plan()
        return self._text(
            "The pending plan was rejected. No authoritative Task or PlanRevision was created."
        )

    def _clear_pending_plan(self) -> None:
        self._pending_objective = None
        self._pending_tasks = ()
        self._pending_plan_revision = None

    def _text(self, content: str) -> Message:
        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=content,
        )

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.contracts import (
    PlannerOutput,
    PlanReviewAction,
    PlanReviewDecision,
)
from cognieda.application.ports import AgentFactoryPort
from cognieda.application.services import PlanAdmissionService
from cognieda.execution import ExecutorDispatcher
from cognieda.schemas.artifacts import SessionFrame, Task
from cognieda.schemas.plan import Plan

from .conversation import ConversationHistory
from .messages import Message, MessageRole, MessageType
from .planner_context import apply_planner_output, build_planner_context
from .workspace import MissingModelCredentialError, Workspace


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
        self._session = session
        self.session_frame = SessionFrame()
        self.conversation_history = ConversationHistory()
        self._pending_plan: Plan | None = None
        self._pending_tasks: tuple[Task, ...] = ()
        self._pending_request: str | None = None

    async def submit_message(self, message: str) -> Message:
        if message.startswith("/"):
            return await self._handle_command(message)

        if self._pending_plan is not None:
            return self._text(
                "A candidate Plan is already awaiting review; approve, reject, or revise it first."
            )

        planner_context = build_planner_context(
            self.session_frame,
            self.conversation_history,
        )
        try:
            planner_output = await self.planner_agent.run(
                message,
                context=planner_context,
            )
        except MissingModelCredentialError as e:
            return self._text(
                f"{e}\n\n"
                "Run '/provider key <provider>' to configure an API key."
            )

        return self._accept_planner_output(planner_output, request=message)

    # TODO: Move command handling to a separate class or module for better separation of concerns
    async def _handle_command(self, command: str) -> Message:
        parts = command.split()

        match parts:
            case ["/approve", raw_plan_id]:
                return await self._review_plan(
                    raw_plan_id,
                    action=PlanReviewAction.APPROVE,
                )

            case [command_name, raw_plan_id, *feedback_parts] if command_name in {
                "/reject",
                "/revise",
            } and feedback_parts:
                return await self._review_plan(
                    raw_plan_id,
                    action=(
                        PlanReviewAction.REJECT
                        if command_name == "/reject"
                        else PlanReviewAction.REVISE
                    ),
                    feedback=" ".join(feedback_parts),
                )

            #
            # Skills
            #
            case ["/skill", "add", name, directory]:
                self.workspace.add_skill(name, directory)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(
                    f"Added skill '{name}'."
                )

            case ["/skill", "rm", name]:
                self.workspace.remove_skill(name)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(
                    f"Removed skill '{name}'."
                )

            case ["/skill", "list"]:
                skills = self.workspace.load_skills_config()

                if not skills:
                    return self._text("No skills registered.")

                return self._text(
                    "\n".join(
                        f"{name}: {cfg['directories']}"
                        for name, cfg in skills.items()
                    )
                )

            case ["/skill", "use", worker, skill]:
                self.workspace.add_worker_skill(worker, skill)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(
                    f"Assigned '{skill}' to '{worker}'."
                )

            case ["/skill", "drop", worker, skill]:
                self.workspace.remove_worker_skill(worker, skill)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(
                    f"Removed '{skill}' from '{worker}'."
                )

            #
            # Providers
            #
            case ["/provider"]:
                profile = self.workspace.project_config.default_provider

                try:
                    self.workspace.project_config.validate()
                except ValueError as e:
                    return self._text(str(e))
                provider = self.workspace.project_config.providers[profile]

                configured = "yes" if provider.api_key_configured() else "no"

                return self._text(
                    f"""Current provider : {profile}
        Model            : {provider.model}
        API key          : {configured}"""
                )

            case ["/provider", "list"]:
                return self._text(
                    "\n".join(
                        self.workspace.project_config.providers.keys()
                    )
                )

            case ["/provider", "use", profile]:
                self.workspace.use_provider(profile)

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(
                    f"Using provider '{profile}'."
                )

            case ["/provider", "model", profile, model]:
                self.workspace.set_provider_model(
                    profile,
                    model,
                )

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(
                    f"Updated '{profile}' model to '{model}'."
                )
            # TODO:
            # Prompting for secrets belongs to the CLI/UI layer.
            # Application should receive the API key as an argument rather than
            # calling input() directly.
            case ["/provider", "key", profile]:
                api_key = input(
                    f"{profile} API key: "
                ).strip()

                self.workspace.set_provider_api_key(
                    profile,
                    api_key,
                )

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(
                    f"Stored API key for '{profile}'."
                )

            #
            # Planner
            #
            case ["/reload"]:
                await self._reload_runtime(
                    reload_instruction=True,
                )

                return self._text(
                    "Planner instructions reloaded."
                )

            case _:
                return self._text(
                    f"Unknown command: '{command}'."
                )

    def _text(self, content: str) -> Message:
        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=content,
        )
    
    async def _reload_runtime(
        self,
        *,
        reload_tooling: bool = False,
        reload_instruction: bool = False,
        recreate_agent: bool = False,
    ) -> None:
        if reload_tooling:
            self.agent_factory.reload_tooling()

        await self.planner_agent.reload(
            model_config=(
                self.workspace.project_config.try_resolve_model()
                if recreate_agent
                else None
            ),
            agent_instruction=(
                self.workspace.load_planner_agent_instruction()
                if reload_instruction
                else None
            ),
            recreate_agent=recreate_agent,
        )

    async def _review_plan(
        self,
        raw_plan_id: str,
        *,
        action: PlanReviewAction,
        feedback: str | None = None,
    ) -> Message:
        try:
            plan_id = UUID(raw_plan_id)
        except ValueError:
            return self._text("Plan review requires an exact UUID Plan identity.")

        plan = self._pending_plan
        if plan is None or plan.plan_id != plan_id:
            return self._text("No pending candidate matches that exact Plan identity.")

        request = self._pending_request or ""
        tasks = self._pending_tasks
        if action is PlanReviewAction.APPROVE:
            if self._session is None:
                return self._text("Plan approval persistence is unavailable.")
            try:
                successor = self._successor_for_approved_plan(plan, tasks)
                PlanAdmissionService(self._session).admit(plan, tasks)
            except Exception as exc:
                return self._text(f"Plan approval failed closed: {exc}")
            self.session_frame = successor

        self._clear_pending_plan()
        planner_output = await self.planner_agent.resume(
            PlanReviewDecision(
                action=action,
                plan_id=plan_id,
                feedback=feedback,
            )
        )
        return self._accept_planner_output(planner_output, request=request)

    def _accept_planner_output(
        self,
        planner_output: PlannerOutput,
        *,
        request: str,
    ) -> Message:
        self.session_frame = apply_planner_output(
            self.session_frame,
            planner_output,
            request=request,
        )
        result = planner_output.cognitive_result
        if result.plan is not None:
            if self._pending_plan is not None:
                raise ValueError("A pending Plan cannot be replaced without Human review.")
            self._pending_plan = result.plan
            self._pending_tasks = result.tasks
            self._pending_request = request
            bundle = {
                "plan": result.plan.model_dump(mode="json"),
                "tasks": [task.model_dump(mode="json") for task in result.tasks],
            }
            return self._text(
                f"{planner_output.response}\n\nHuman-review bundle:\n{bundle}"
            )

        if planner_output.messages:
            self.conversation_history = self.conversation_history.add_turn(
                planner_output.messages
            )
        return self._text(planner_output.response)

    def _successor_for_approved_plan(
        self,
        plan: Plan,
        tasks: tuple[Task, ...],
    ) -> SessionFrame:
        current = self.session_frame
        if current.objective is not None and current.objective != plan.objective:
            raise ValueError(
                "Replacing an active Objective without an exact successor contract is unsupported."
            )

        assumptions_by_id = {item.assumption_id: item for item in current.assumptions}
        for assumption in plan.assumptions:
            assumption_existing = assumptions_by_id.get(assumption.assumption_id)
            if assumption_existing is not None and assumption_existing != assumption:
                raise ValueError("Approved Assumption identity conflicts with retained content.")
            assumptions_by_id[assumption.assumption_id] = assumption

        tasks_by_id = {item.task_id: item for item in current.tasks}
        for task in tasks:
            task_existing = tasks_by_id.get(task.task_id)
            if task_existing is not None and task_existing != task:
                raise ValueError("Approved Task identity conflicts with retained content.")
            tasks_by_id[task.task_id] = task

        return SessionFrame(
            objective=plan.objective,
            assumptions=tuple(assumptions_by_id.values()),
            tasks=tuple(tasks_by_id.values()),
            evidences=current.evidences,
            discoveries=current.discoveries,
            data_profile=current.data_profile,
        )

    def _clear_pending_plan(self) -> None:
        self._pending_plan = None
        self._pending_tasks = ()
        self._pending_request = None

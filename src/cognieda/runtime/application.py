from __future__ import annotations

from getpass import getpass

from sqlmodel import Session

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.types import PlannerResult
from cognieda.application.ports import AgentFactoryPort
from cognieda.delegation import ExecutorDispatcher
from cognieda.infrastructure.persistence.repositories import ActivePlanRepository
from cognieda.runtime.event_bus import EventBus
from cognieda.runtime.events import HumanInputRequested, MessageProduced, PlanProposed
from cognieda.schemas.artifacts import SessionFrame
from cognieda.schemas.plan import Plan
from cognieda.runtime.commands import (
    CommandContext,
    CommandHandler,
    CommandParser,
    create_command_registry,
)

from .conversation import ConversationHistory
from .messages import Message, MessageRole, MessageType
from .planner_context import build_planner_context
from .workspace import MissingModelCredentialError, Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        dispatcher: ExecutorDispatcher,
        agent_factory: AgentFactoryPort,
        event_bus: EventBus,
        session: Session,
    ) -> None:
        self.workspace = workspace
        self.agent_factory = agent_factory
        self.planner_agent = planner_agent
        self.event_bus = event_bus
        self.dispatcher = dispatcher
        self._active_plans = ActivePlanRepository(session)
        self.session_frame = SessionFrame()
        self.conversation_history = ConversationHistory()

        self.command_handler = CommandHandler(
            parser=CommandParser(),
            registry=create_command_registry(),
            context=CommandContext(
                workspace=self.workspace,
                agent_factory=self.agent_factory,
                planner=self.planner_agent,
                reload_runtime=self._reload_runtime,
                prompt_secret=getpass,
            ),
        )

    async def submit_message(self, message: str) -> None:
        if message.startswith("/"):
            command_result = await self.command_handler.handle(message)
            self.event_bus.publish(
                MessageProduced(message=command_result)
            )
            return

        active_plan = self._resolve_active_plan()
        planner_context = build_planner_context(
            self.session_frame,
            active_plan=active_plan,
        )

        try:
            planner_output = await self.planner_agent.run(
                message,
                context=planner_context,
                message_history=self.conversation_history.model_messages(),
            )
        except MissingModelCredentialError as e:
            self._emit_message(f"{e}\n\nRun '/provider key <provider>' to configure an API key.")
            return

        if planner_output.messages:
            self.conversation_history = self.conversation_history.add_turn(planner_output.messages)

        self._emit_planner_result(planner_output.result)

    def _resolve_active_plan(self) -> Plan | None:
        objective = self.session_frame.objective
        if objective is None:
            return None
        return self._active_plans.get_by_objective_id(objective.objective_id)

    def _emit_planner_result(self, result: PlannerResult) -> None:
        if result.plan is not None:
            self.event_bus.publish(
                PlanProposed(
                    plan=result.plan,
                    tasks=result.tasks,
                )
            )
            return

        if result.response is not None:
            self._emit_message(result.response)
            return

        if result.human_input_request is not None:
            self.event_bus.publish(
                HumanInputRequested(
                    message=Message(
                        type=MessageType.TEXT,
                        role=MessageRole.ASSISTANT,
                        content=result.human_input_request,
                    )
                )
            )
            return

        if result.continue_execution:
            # No public event yet.
            return

        raise AssertionError("PlannerResult passed validation but has no conclusion.")

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
                self.workspace.project_config.try_resolve_model() if recreate_agent else None
            ),
            agent_instruction=(
                self.workspace.load_agent_instruction() if reload_instruction else None
            ),
            recreate_agent=recreate_agent,
        )

    def _emit_message(self, content: str) -> None:
        self.event_bus.publish(
            MessageProduced(
                message=Message(
                    type=MessageType.TEXT,
                    role=MessageRole.ASSISTANT,
                    content=content,
                )
            )
        )

from __future__ import annotations

from collections.abc import Callable
from getpass import getpass
from uuid import UUID

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.state import PlannerTurnOutcome
from cognieda.application.ports import AgentFactoryPort
from cognieda.runtime.commands import (
    CommandContext,
    CommandHandler,
    CommandParser,
    create_command_registry,
)
from cognieda.runtime.commands.types import CommandSuggestion
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.event_bus import EventBus
from cognieda.runtime.events import HumanInputRequested, MessageProduced, PlanProposed

from .messages import Message, MessageRole, MessageType
from .workspace import MissingModelCredentialError, Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        agent_factory: AgentFactoryPort,
        event_bus: EventBus,
        session_id: UUID,
        conversation_history: ConversationHistory,
        planner_context_factory: Callable[[], PlannerContext],
    ) -> None:
        self.workspace = workspace
        self.agent_factory = agent_factory
        self.planner_agent = planner_agent
        self.event_bus = event_bus
        self.session_id = session_id
        self.conversation_history = conversation_history
        self.planner_context_factory = planner_context_factory

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

    def suggest_commands(
        self,
        prefix: str,
    ) -> tuple[CommandSuggestion, ...]:
        return self.command_handler.suggest(prefix)

    async def submit_message(self, message: str) -> None:
        self.event_bus.publish(
            MessageProduced(
                message=Message(
                    type=MessageType.TEXT,
                    role=MessageRole.USER,
                    content=message,
                )
            )
        )

        if message.startswith("/"):
            command_result = await self.command_handler.handle(message)
            self.event_bus.publish(
                MessageProduced(message=command_result)
            )
            return

        try:
            context = self.planner_context_factory()
        except Exception:
            self._emit_message(
                "Planner authoritative context could not be materialized.",
                message_type=MessageType.ERROR,
            )
            return

        message_history = tuple(self.conversation_history.model_messages())

        try:
            outcome, completed_segments = await self.planner_agent.handle_message(
                message,
                context=context,
                message_history=message_history,
            )
        except MissingModelCredentialError as e:
            self._emit_message(f"{e}\n\nRun '/provider key <provider>' to configure an API key.")
            return

        if completed_segments:
            self.conversation_history = self.conversation_history.add_turn(completed_segments)

        self._emit_planner_outcome(outcome)

    def _emit_planner_outcome(self, outcome: PlannerTurnOutcome) -> None:
        if outcome.error is not None:
            self._emit_message(outcome.error.message, message_type=MessageType.ERROR)
            return

        if outcome.proposed_plan is not None:
            self.event_bus.publish(PlanProposed(plan=outcome.proposed_plan))

        if outcome.response is not None:
            self._emit_message(outcome.response)

        if outcome.human_input_request is not None:
            self.event_bus.publish(
                HumanInputRequested(
                    message=Message(
                        type=MessageType.TEXT,
                        role=MessageRole.ASSISTANT,
                        content=outcome.human_input_request,
                    )
                )
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
                self.workspace.project_config.try_resolve_model() if recreate_agent else None
            ),
            agent_instruction=(
                self.workspace.load_agent_instruction() if reload_instruction else None
            ),
            recreate_agent=recreate_agent,
        )

    def _emit_message(
        self,
        content: str,
        *,
        message_type: MessageType = MessageType.TEXT,
    ) -> None:
        self.event_bus.publish(
            MessageProduced(
                message=Message(
                    type=message_type,
                    role=MessageRole.ASSISTANT,
                    content=content,
                )
            )
        )


__all__ = ("Application",)

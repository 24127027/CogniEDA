from __future__ import annotations

from getpass import getpass
from typing import Callable
from uuid import UUID

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.state import PlannerTurnOutcome
from cognieda.application.ports import AgentFactoryPort
from cognieda.runtime.conversation.history import ConversationHistory
from cognieda.runtime.event_bus import EventBus
from cognieda.runtime.events import (
    ModelMessageProduced,
    MessageProduced, 
    PlanProposed, 
    AssistantThinkingStarted, 
    AssistantThinkingFinished,
    SegmentCompleted, 
    TurnCompleted
)
from cognieda.runtime.commands.types import CommandSuggestion
from cognieda.runtime.commands import (
    CommandContext,
    CommandHandler,
    CommandParser,
    create_command_registry,
)

from .projection.message import MessageProjector
from .conversation.projector import ConversationProjector
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
        message_projector: MessageProjector,
        conversation_projector: ConversationProjector,
    ) -> None:
        self.workspace = workspace
        self.agent_factory = agent_factory
        self.planner_agent = planner_agent
        self.event_bus = event_bus
        self.session_id = session_id
        self.conversation_history = conversation_history
        self.planner_context_factory = planner_context_factory
        self.message_projector = message_projector
        self.conversation_projector = conversation_projector

        print()

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
        # TODO: 
        # Keep this publication here, or place it inside message projector
        await self.event_bus.publish(
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
            await self.event_bus.publish(
                MessageProduced(message=command_result)
            )
            return

        try:
            context = self.planner_context_factory()
        except Exception:
            await self._emit_message(
                "Planner authoritative context could not be materialized.",
                message_type=MessageType.ERROR,
            )
            return

        message_history = tuple(self.conversation_history.model_messages())

        try:
            await self.event_bus.publish(AssistantThinkingStarted())
            outcome, completed_segment = await self.planner_agent.handle_message(
                message,
                context=context,
                message_history=message_history,
            )
            await self.event_bus.publish(AssistantThinkingFinished())
        except MissingModelCredentialError as e:
            await self._emit_message(f"{e}\n\nRun '/provider key <provider>' to configure an API key.")
            return

        # TODO: This is a temporary solution to emit the completed segment messages. 
        # These should be emitted by the planner agent in the future.
        if completed_segment is not None:
            for msg in completed_segment.messages:
                await self.event_bus.publish(ModelMessageProduced(message=msg))
            await self.event_bus.publish(SegmentCompleted())
            await self.event_bus.publish(TurnCompleted())

        await self._emit_planner_outcome(outcome)

    async def _emit_planner_outcome(self, outcome: PlannerTurnOutcome) -> None:
        if outcome.error is not None:
            await self._emit_message(outcome.error.message, message_type=MessageType.ERROR)
            return

        if outcome.proposed_plan is not None:
            await self.event_bus.publish(PlanProposed(plan=outcome.proposed_plan))

        if outcome.response is not None:
            await self._emit_message(outcome.response)

        if outcome.human_input_request is not None:
            await self.event_bus.publish(
                MessageProduced(
                    message=Message(
                        type=MessageType.INPUT_REQUEST,
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

    async def _emit_message(
        self,
        content: str,
        *,
        message_type: MessageType = MessageType.TEXT,
    ) -> None:
        await self.event_bus.publish(
            MessageProduced(
                message=Message(
                    type=message_type,
                    role=MessageRole.ASSISTANT,
                    content=content,
                )
            )
        )


__all__ = ("Application",)

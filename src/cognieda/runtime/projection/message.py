from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from cognieda.runtime.conversation.history import ConversationHistory
from cognieda.runtime.event_bus import EventBus
from cognieda.runtime.events import MessageProduced, ModelMessageProduced
from cognieda.runtime.messages import Message, MessageRole, MessageType


@dataclass(frozen=True, slots=True)
class MessageProjection:
    """UI-facing projection of one native Pydantic AI model message."""

    messages: tuple[Message, ...]


class MessageProjector:
    """Project native model history/messages into application Messages."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    async def handle(self, event: ModelMessageProduced) -> None:
        if not event.visible:
            return

        projection = self.project(event.message)

        for message in projection.messages:
            await self.event_bus.publish(
                MessageProduced(message=message)
            )

    def project(
        self,
        model_message: ModelMessage,
    ) -> MessageProjection:
        if isinstance(model_message, ModelRequest):
            return self._project_request(model_message)

        if isinstance(model_message, ModelResponse):
            return self._project_response(model_message)

        return MessageProjection(messages=())

    def project_history(
        self,
        history: ConversationHistory,
    ) -> tuple[Message, ...]:
        messages: list[Message] = []

        for turn in history.turns:
            for segment in turn.segments:
                for model_message in segment.messages:
                    messages.extend(
                        self.project(model_message).messages
                    )

        return tuple(messages)

    def _project_request(
        self,
        message: ModelRequest,
    ) -> MessageProjection:
        projected: list[Message] = []

        for part in message.parts:
            # TODO: application.submit_message already handle this, choose one place
            # if isinstance(part, UserPromptPart):
            #     projected.append(
            #         Message(
            #             role=MessageRole.USER,
            #             type=MessageType.TEXT,
            #             content=str(part.content),
            #         )
            #     )

            if isinstance(part, ToolReturnPart):
                # TODO: temporarily filter final results from tool calls, 
                # until we have a better way to handle them
                if part.tool_name == "final_result":
                    continue

                projected.append(
                    Message(
                        role=MessageRole.ASSISTANT,
                        type=MessageType.TEXT,
                        content=f"Tool result: {part.tool_name}",
                    )
                )

            elif isinstance(part, SystemPromptPart):
                # Model context, not an application-facing message.
                continue

        return MessageProjection(messages=tuple(projected))

    def _project_response(
        self,
        message: ModelResponse,
    ) -> MessageProjection:
        projected: list[Message] = []

        for part in message.parts:
            if isinstance(part, TextPart):
                projected.append(
                    Message(
                        role=MessageRole.ASSISTANT,
                        type=MessageType.TEXT,
                        content=part.content,
                        model=message.model_name,
                    )
                )

            elif isinstance(part, ToolCallPart):
                # TODO: temporarily filter final results from tool calls, 
                # until we have a better way to handle them
                if part.tool_name == "final_result":
                    continue

                projected.append(
                    Message(
                        role=MessageRole.ASSISTANT,
                        type=MessageType.TEXT,
                        content=f"Calling tool: {part.tool_name}",
                        model=message.model_name,
                    )
                )

        return MessageProjection(messages=tuple(projected))
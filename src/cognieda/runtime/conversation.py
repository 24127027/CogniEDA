from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from cognieda.schemas.common import ImmutableCogniEDABaseModel


class ConversationTurn(ImmutableCogniEDABaseModel):
    """One retained Planner turn in native PydanticAI protocol form."""

    turn_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ModelMessage, ...]

    @model_validator(mode="after")
    def _messages_not_empty(self) -> ConversationTurn:
        if not self.messages:
            raise ValueError("ConversationTurn requires at least one ModelMessage.")
        return self


class ConversationHistory(ImmutableCogniEDABaseModel):
    """Ordered native interaction history retained by one runtime Session."""

    turns: tuple[ConversationTurn, ...] = ()

    @model_validator(mode="after")
    def _unique_turn_ids(self) -> ConversationHistory:
        turn_ids = [turn.turn_id for turn in self.turns]
        if len(turn_ids) != len(set(turn_ids)):
            raise ValueError("ConversationHistory rejects duplicate ConversationTurn IDs.")
        return self

    def add_turn(self, messages: Iterable[ModelMessage]) -> ConversationHistory:
        """Append one complete, unsplit protocol sequence as an immutable successor."""

        turn = ConversationTurn(messages=tuple(messages))
        return ConversationHistory(turns=(*self.turns, turn))

    def model_messages(self) -> tuple[ModelMessage, ...]:
        """Flatten only at the PydanticAI invocation boundary."""

        return tuple(message for turn in self.turns for message in turn.messages)

    def select_for_request_understanding(self) -> tuple[ModelMessage, ...]:
        """Return the currently eligible whole-turn history for request understanding."""

        return self.model_messages()


def planner_interaction_messages(
    *, human_message: str, planner_message: str
) -> tuple[ModelMessage, ...]:
    """Represent a model-free Planner command turn without a lossy custom transcript."""

    return (
        ModelRequest(parts=[UserPromptPart(content=human_message)]),
        ModelResponse(parts=[TextPart(content=planner_message)]),
    )

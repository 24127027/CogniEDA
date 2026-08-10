from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.common import CogniEDABaseModel


class ConversationSegment(CogniEDABaseModel):
    """A coherent native-message unit reserved for finer-grained future history."""

    segment_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ModelMessage, ...]


class ConversationTurn(CogniEDABaseModel):
    """One complete Planner/LangGraph run retained as native model messages."""

    turn_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ModelMessage, ...]

    @model_validator(mode="after")
    def _messages_not_empty(self) -> ConversationTurn:
        if not self.messages:
            raise ValueError("ConversationTurn requires at least one ModelMessage.")
        return self


class ConversationHistory(CogniEDABaseModel):
    """Append-only ordered history of complete Planner runs."""

    turns: tuple[ConversationTurn, ...] = ()

    @model_validator(mode="after")
    def _unique_turn_ids(self) -> ConversationHistory:
        turn_ids = [turn.turn_id for turn in self.turns]
        if len(turn_ids) != len(set(turn_ids)):
            raise ValueError("ConversationHistory rejects duplicate ConversationTurn IDs.")
        return self

    def add_turn(self, messages: Iterable[ModelMessage]) -> ConversationHistory:
        turn = ConversationTurn(messages=tuple(messages))
        return ConversationHistory(turns=(*self.turns, turn))

    def model_messages(self) -> list[ModelMessage]:
        """Flatten complete turns for PydanticAI message_history."""

        return [message for turn in self.turns for message in turn.messages]

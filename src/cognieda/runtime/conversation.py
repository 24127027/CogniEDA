from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from pydantic_ai.messages import ModelMessage, ToolCallPart, ToolReturnPart

from cognieda.schemas.common import ImmutableCogniEDABaseModel


class ConversationSegment(ImmutableCogniEDABaseModel):
    """One indivisible, coherent native model-history unit."""

    segment_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ModelMessage, ...]

    @model_validator(mode="after")
    def _messages_form_complete_unit(self) -> ConversationSegment:
        if not self.messages:
            raise ValueError("ConversationSegment requires at least one ModelMessage.")

        calls = Counter(
            (part.tool_call_id, part.tool_name)
            for message in self.messages
            for part in message.parts
            if isinstance(part, ToolCallPart)
        )
        returns = Counter(
            (part.tool_call_id, part.tool_name)
            for message in self.messages
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        )
        if calls != returns:
            raise ValueError(
                "ConversationSegment must retain matching tool-call/tool-return pairs."
            )
        return self


class ConversationTurn(ImmutableCogniEDABaseModel):
    """One complete Human/Planner surface interaction and its native model runs."""

    turn_id: UUID = Field(default_factory=uuid4)
    human_message: str = Field(min_length=1)
    planner_response: str = Field(min_length=1)
    segments: tuple[ConversationSegment, ...] = ()

    @model_validator(mode="after")
    def _unique_segment_ids(self) -> ConversationTurn:
        segment_ids = [segment.segment_id for segment in self.segments]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("ConversationTurn rejects duplicate ConversationSegment IDs.")
        return self


class ConversationHistory(ImmutableCogniEDABaseModel):
    """Complete ordered Human/Planner history retained by one runtime Session."""

    turns: tuple[ConversationTurn, ...] = ()

    @model_validator(mode="after")
    def _unique_turn_ids(self) -> ConversationHistory:
        turn_ids = [turn.turn_id for turn in self.turns]
        if len(turn_ids) != len(set(turn_ids)):
            raise ValueError("ConversationHistory rejects duplicate ConversationTurn IDs.")
        segment_ids = [segment.segment_id for turn in self.turns for segment in turn.segments]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("ConversationHistory rejects duplicate ConversationSegment IDs.")
        return self

    def add_turn(
        self,
        *,
        human_message: str,
        planner_response: str,
        message_segments: Iterable[Iterable[ModelMessage]] = (),
    ) -> ConversationHistory:
        """Append one surface turn and each complete native model run as a segment."""

        turn = ConversationTurn(
            human_message=human_message,
            planner_response=planner_response,
            segments=tuple(
                ConversationSegment(messages=tuple(messages)) for messages in message_segments
            ),
        )
        return ConversationHistory(turns=(*self.turns, turn))

    def model_messages(self) -> tuple[ModelMessage, ...]:
        """Flatten complete segments only at the PydanticAI invocation boundary."""

        return tuple(
            message
            for turn in self.turns
            for segment in turn.segments
            for message in segment.messages
        )

    def select_for_request_understanding(self) -> tuple[ModelMessage, ...]:
        """Return complete retained segments until the policy selector is applied."""

        return self.model_messages()

    def presentation_transcript(self) -> tuple[tuple[str, str], ...]:
        """Return the non-authoritative Human/Planner surface transcript."""

        return tuple((turn.human_message, turn.planner_response) for turn in self.turns)

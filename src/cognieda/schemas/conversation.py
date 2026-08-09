from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.common import CogniEDABaseModel

class ConversationSegment(CogniEDABaseModel):
    """
    Coherent unit of model interaction that may be retained or excluded
    independently when constructing future conversation context.

    A segment groups a sequence of ModelMessage objects that should remain
    together to preserve conversational and tool-call consistency. In
    particular, boundaries must not separate dependent interactions such as
    a tool call from its corresponding tool result.

    For the MVP, a ConversationTurn may contain a single segment representing
    the complete Planner run. In later versions, long-running Planner workflows
    may produce multiple segments so that valid intermediate work can remain
    available even when a later portion of the same turn is discarded,
    superseded, or excluded from active context.

    Segment boundaries represent semantic context-recovery boundaries, not
    LangGraph node boundaries. LangGraph execution checkpoints and durable
    research objects remain separate mechanisms for restoring workflow state
    and preserving authoritative analytical results.
    """

    segment_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ModelMessage, ...]

# TODO: After MVP, consider adding a ConversationSegment
# to ConversationTurn relationship to allow multiple segments per turn.
class ConversationTurn(CogniEDABaseModel):
    """
    User-level interaction containing one or more coherent conversation segments.

    A turn begins with one user interaction and may span multiple model calls,
    tool executions, and LangGraph steps. Segmentation allows parts of a long
    turn to be managed independently without changing the user-level turn
    boundary.
    """

    turn_id: UUID = Field(default_factory=uuid4)
    #segments: tuple[ConversationSegment, ...]
    messages: tuple[ModelMessage, ...]

    @model_validator(mode="after")
    def _messages_not_empty(self) -> ConversationTurn:
        if not self.messages:
            raise ValueError("ConversationTurn requires at least one ModelMessage.")
        return self


class ConversationHistory(CogniEDABaseModel):
    """Ordered conversation turns for the active MVP session."""

    turns: tuple[ConversationTurn, ...] = ()

    @model_validator(mode="after")
    def _unique_turn_ids(self) -> ConversationHistory:
        ids = [turn.turn_id for turn in self.turns]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "ConversationHistory rejects duplicate ConversationTurn IDs."
            )

        return self

    def add_turn(
        self,
        messages: Iterable[ModelMessage],
    ) -> ConversationHistory:
        turn = ConversationTurn(messages=tuple(messages))

        return ConversationHistory(
            turns=(*self.turns, turn),
        )

    def model_messages(self) -> list[ModelMessage]:
        """Flatten complete turns for Pydantic AI message_history."""
        return [
            message
            for turn in self.turns
            for message in turn.messages
        ]
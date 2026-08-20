from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.common import CogniEDABaseModel


class ConversationSegment(CogniEDABaseModel):
    """One indivisible native model-history retention and pruning unit."""

    segment_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ModelMessage, ...] = ()

    @model_validator(mode="after")
    def _messages_not_empty(self) -> ConversationSegment:
        if not self.messages:
            raise ValueError("ConversationSegment requires at least one ModelMessage.")
        return self


class ConversationTurn(CogniEDABaseModel):
    """One ordered, non-authoritative unit of native conversation memory."""

    turn_id: UUID = Field(default_factory=uuid4)
    segments: tuple[ConversationSegment, ...] = ()

    @model_validator(mode="after")
    def _segments_not_empty(self) -> ConversationTurn:
        if not self.segments:
            raise ValueError("ConversationTurn requires at least one ConversationSegment.")
        segment_ids = [segment.segment_id for segment in self.segments]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("ConversationTurn rejects duplicate ConversationSegment IDs.")
        return self

    @property
    def messages(self) -> tuple[ModelMessage, ...]:
        """Flatten native messages across all segments in this turn."""

        return tuple(
            message for segment in self.segments for message in segment.messages
        )


class ConversationHistory(CogniEDABaseModel):
    """Append-only native conversation memory, separate from research authority."""

    _turns: list[ConversationTurn] = []

    @property
    def turns(self) -> tuple[ConversationTurn, ...]:
        return tuple(self._turns)

    @model_validator(mode="after")
    def _unique_ids(self) -> ConversationHistory:
        turn_ids = [turn.turn_id for turn in self._turns]
        if len(turn_ids) != len(set(turn_ids)):
            raise ValueError("ConversationHistory rejects duplicate ConversationTurn IDs.")
        segment_ids = [
            segment.segment_id
            for turn in self.turns
            for segment in turn.segments
        ]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError(
                "ConversationHistory rejects duplicate ConversationSegment IDs."
            )
        return self

    def commit_segment(self, segment: ConversationSegment) -> None:
        """Append one completed ConversationSegment as a successor turn."""

        turn = ConversationTurn(segments=(segment,))
        self._turns.append(turn)

    def add_turn(
        self,
        segments: Iterable[ConversationSegment],
    ) -> None:
        self._turns.append(
            ConversationTurn(
                segments=tuple(segments),
            )
        )

    def truncate_from(self, segment_id: UUID) -> None:
        """Remove the identified segment and all causally subsequent conversation."""

        found = False
        retained_turns: list[ConversationTurn] = []

        for turn in self.turns:
            if found:
                break

            segment_ids = [segment.segment_id for segment in turn.segments]
            if segment_id in segment_ids:
                found = True
                index = segment_ids.index(segment_id)
                retained_segments = turn.segments[:index]
                if retained_segments:
                    retained_turns.append(
                        ConversationTurn(
                            turn_id=turn.turn_id,
                            segments=retained_segments,
                        )
                    )
            else:
                retained_turns.append(turn)

        if not found:
            raise ValueError(
                f"ConversationSegment '{segment_id}' not found in ConversationHistory."
            )

        self._turns=retained_turns

    def model_messages(self) -> list[ModelMessage]:
        """Flatten turns and segments in exact append and native-message order."""

        return [
            message
            for turn in self.turns
            for segment in turn.segments
            for message in segment.messages
        ]


__all__ = (
    "ConversationHistory",
    "ConversationSegment",
    "ConversationTurn",
)

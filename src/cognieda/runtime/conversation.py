from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from uuid import UUID, uuid4

from pydantic import Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.common import ImmutableCogniEDABaseModel

DEFAULT_RECENT_TURN_LIMIT = 4
DEFAULT_OLDER_LEXICAL_MATCH_LIMIT = 4


class ConversationSegment(ImmutableCogniEDABaseModel):
    """One indivisible native model-history retention and pruning unit."""

    segment_id: UUID = Field(default_factory=uuid4)
    messages: tuple[ModelMessage, ...] = Field(min_length=1)


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

    def presentation_transcript(self) -> tuple[tuple[str, str], ...]:
        """Return the non-authoritative Human/Planner surface transcript."""

        return tuple((turn.human_message, turn.planner_response) for turn in self.turns)


def select_conversation_context(
    history: ConversationHistory,
    latest_request: str,
    *,
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT,
    older_lexical_match_limit: int = DEFAULT_OLDER_LEXICAL_MATCH_LIMIT,
) -> tuple[ConversationTurn, ...]:
    """Select bounded surface discourse without mutating retained history."""

    if recent_turn_limit < 1:
        raise ValueError("recent_turn_limit must be positive.")
    if older_lexical_match_limit < 0:
        raise ValueError("older_lexical_match_limit cannot be negative.")
    request_terms = _selection_terms(latest_request)
    recent_start = max(0, len(history.turns) - recent_turn_limit)
    older_match_indexes: list[int] = []
    if older_lexical_match_limit:
        for index in range(recent_start - 1, -1, -1):
            turn = history.turns[index]
            surface_terms = _selection_terms(
                f"{turn.human_message} {turn.planner_response}"
            )
            if request_terms.intersection(surface_terms):
                older_match_indexes.append(index)
                if len(older_match_indexes) == older_lexical_match_limit:
                    break

    selected_indexes = sorted((*older_match_indexes, *range(recent_start, len(history.turns))))
    return tuple(history.turns[index] for index in selected_indexes)


def _selection_terms(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return {
        term
        for term in re.findall(r"\w+", normalized, flags=re.UNICODE)
        if len(term) >= 3
    }

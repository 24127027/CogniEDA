from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field, model_validator

from cognieda.schemas.common import ImmutableCogniEDABaseModel, NonEmptyStr


class ConversationTurn(ImmutableCogniEDABaseModel):
    """One Human-to-Planner interaction exactly as presented at the runtime boundary."""

    turn_id: UUID = Field(default_factory=uuid4)
    human_message: str
    planner_message: NonEmptyStr


class ConversationHistory(ImmutableCogniEDABaseModel):
    """Ordered append-only Human-to-Planner turns for one runtime Session."""

    turns: tuple[ConversationTurn, ...] = ()

    @model_validator(mode="after")
    def _unique_turn_ids(self) -> ConversationHistory:
        turn_ids = [turn.turn_id for turn in self.turns]
        if len(turn_ids) != len(set(turn_ids)):
            raise ValueError("ConversationHistory rejects duplicate ConversationTurn IDs.")
        return self

    def append(self, *, human_message: str, planner_message: str) -> ConversationHistory:
        turn = ConversationTurn(
            turn_id=uuid4(),
            human_message=human_message,
            planner_message=planner_message,
        )
        return ConversationHistory(turns=(*self.turns, turn))

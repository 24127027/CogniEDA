from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import Field
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import SessionFrame
from cognieda.schemas.common import ImmutableCogniEDABaseModel

from .conversation import ConversationHistory


class Session(ImmutableCogniEDABaseModel):
    """Runtime lifetime aggregate for one active Human-to-Planner chat."""

    session_id: UUID = Field(default_factory=uuid4)
    session_frame: SessionFrame = Field(default_factory=SessionFrame)
    conversation_history: ConversationHistory = Field(default_factory=ConversationHistory)

    def advance(
        self,
        *,
        session_frame: SessionFrame,
        messages: tuple[ModelMessage, ...],
    ) -> Session:
        """Return the coherent successor after one completed Planner turn."""

        return Session(
            session_id=self.session_id,
            session_frame=session_frame,
            conversation_history=self.conversation_history.add_turn(messages),
        )

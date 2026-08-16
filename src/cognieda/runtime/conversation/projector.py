from pydantic_ai.messages import ModelMessage

from cognieda.runtime.events import (
    ModelMessageProduced,
    SegmentCompleted,
    TurnCompleted,
)
from cognieda.runtime.conversation.history import (
    ConversationHistory,
    ConversationSegment,
)


class ConversationProjector:
    def __init__(
        self,
        history: ConversationHistory,
    ) -> None:
        self.history = history

        self._current_messages: list[ModelMessage] = []
        self._pending_segments: list[ConversationSegment] = []

    def handle(
        self,
        event: ModelMessageProduced,
    ) -> None:
        self._current_messages.append(event.message)

    def handle_segment_completed(
        self,
        event: SegmentCompleted,
    ) -> None:
        if not self._current_messages:
            raise RuntimeError(
                "Cannot complete segment without ModelMessages."
            )

        segment = ConversationSegment(
            messages=tuple(self._current_messages),
        )

        self._current_messages.clear()
        self._pending_segments.append(segment)

    def handle_turn_completed(
        self,
        event: TurnCompleted,
    ) -> None:
        if not self._pending_segments:
            raise RuntimeError(
                "Cannot complete turn without segments."
            )

        self.history = self.history.add_turn(
            self._pending_segments
        )

        self._pending_segments.clear()
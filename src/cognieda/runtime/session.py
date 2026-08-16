from __future__ import annotations

from uuid import UUID, uuid4

from pydantic_ai.messages import ModelMessage

from cognieda.agents.planner.context import PlannerContext
from cognieda.infrastructure.persistence.repositories import (
    ActivePlanRepository,
    SessionFrameRepository,
)
from cognieda.runtime.conversation import ConversationHistory, ConversationSegment
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas.artifacts import SessionFrame


class ChatSession:
    """One active chat session owning conversational memory and session identity."""

    def __init__(
        self,
        *,
        session_id: UUID | None = None,
        conversation_history: ConversationHistory | None = None,
        session_frames: SessionFrameRepository | None = None,
        active_plans: ActivePlanRepository | None = None,
    ) -> None:
        self.session_id = session_id or uuid4()
        self.conversation_history = conversation_history or ConversationHistory()
        self._session_frames = session_frames
        self._active_plans = active_plans

    def get_session_frame(self) -> SessionFrame:
        """Return the current authoritative SessionFrame for this session."""

        if self._session_frames is None:
            return SessionFrame()
        return self._session_frames.get_current()

    def save_session_frame(self, frame: SessionFrame) -> SessionFrame:
        """Persist a new authoritative SessionFrame snapshot for this session."""

        if self._session_frames is None:
            return frame
        return self._session_frames.save_current(frame)

    def current_planner_context(self) -> PlannerContext:
        """Materialize the fresh authoritative PlannerContext for this turn."""

        frame = self.get_session_frame()
        active_plan = None
        if self._active_plans is not None and frame.objective is not None:
            active_plan = self._active_plans.get_by_objective_id(
                frame.objective.objective_id
            )
        return build_planner_context(frame, active_plan=active_plan)

    def commit_segment(self, segment: ConversationSegment) -> None:
        """Commit one completed ConversationSegment to conversational memory."""

        self.conversation_history = self.conversation_history.commit_segment(segment)

    def truncate_from(self, segment_id: UUID) -> None:
        """Remove the identified segment and all causally subsequent conversation."""

        self.conversation_history = self.conversation_history.truncate_from(segment_id)

    def model_messages(self) -> list[ModelMessage]:
        """Flatten retained conversational memory for model invocation."""

        return self.conversation_history.model_messages()


__all__ = ("ChatSession",)

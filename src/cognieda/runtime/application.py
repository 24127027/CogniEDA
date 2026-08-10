from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import NonAuthoritativeSurfaceTurn
from cognieda.execution import ExecutorDispatcher

from .conversation import ConversationSegment, select_conversation_context
from .messages import Message, MessageRole, MessageType
from .planner_context import (
    PlannerContextPreparer,
    PlanningContextResolutionError,
    select_planner_context,
)
from .session import Session
from .workspace import Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        planner_context_preparer: PlannerContextPreparer,
        dispatcher: ExecutorDispatcher,
        session: Session | None = None,
    ) -> None:
        self.workspace = workspace
        self.planner_agent = planner_agent
        self.planner_context_preparer = planner_context_preparer
        self.dispatcher = dispatcher
        self.session = session or Session()

    async def submit_message(self, message: str) -> Message:
        selected_turns = select_conversation_context(
            self.session.conversation_history,
            message,
        )
        surface_discourse = tuple(
            NonAuthoritativeSurfaceTurn(
                human_message=turn.human_message,
                planner_response=turn.planner_response,
            )
            for turn in selected_turns
        )
        try:
            selection = select_planner_context(self.session.session_frame)
            planning_context = self.planner_context_preparer.build(
                latest_request=message,
                selection=selection,
                surface_discourse=surface_discourse,
            )
        except PlanningContextResolutionError as exc:
            response = f"Planner context resolution failed closed: {exc}"
            self.session = self.session.advance(
                session_frame=self.session.session_frame,
                human_message=message,
                planner_response=response,
                segments=(),
            )
            return Message(type=MessageType.TEXT, role=MessageRole.ASSISTANT, content=response)

        planner_output = await self.planner_agent.run(
            message,
            planning_context=planning_context,
            session_frame=self.session.session_frame,
        )
        segments = tuple(
            ConversationSegment(messages=messages)
            for messages in planner_output.new_message_segments
        )
        self.session = self.session.advance(
            session_frame=planner_output.session_frame,
            human_message=message,
            planner_response=planner_output.response,
            segments=segments,
        )

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=planner_output.response,
        )

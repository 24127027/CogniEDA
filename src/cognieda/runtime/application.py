from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.execution import ExecutorDispatcher

from .conversation import ConversationSegment
from .messages import Message, MessageRole, MessageType
from .session import Session
from .workspace import Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        dispatcher: ExecutorDispatcher,
        session: Session | None = None,
    ) -> None:
        self.workspace = workspace
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher
        self.session = session or Session()

    async def submit_message(self, message: str) -> Message:
        selected_segments = self.session.conversation_history.select_for_request_understanding(
            message
        )
        planner_output = await self.planner_agent.run(
            message,
            session_frame=self.session.session_frame,
            message_history=tuple(
                native_message
                for segment in selected_segments
                for native_message in segment.messages
            ),
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

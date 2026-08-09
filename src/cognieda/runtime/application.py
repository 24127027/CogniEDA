from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.execution import ExecutorDispatcher

from .conversation import planner_interaction_messages
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
        planner_output = await self.planner_agent.run(
            message,
            session_frame=self.session.session_frame,
            message_history=(
                self.session.conversation_history.select_for_request_understanding()
            ),
        )
        turn_messages = planner_output.new_messages or planner_interaction_messages(
            human_message=message,
            planner_message=planner_output.response,
        )
        self.session = self.session.advance(
            session_frame=planner_output.session_frame,
            messages=turn_messages,
        )

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=planner_output.response,
        )

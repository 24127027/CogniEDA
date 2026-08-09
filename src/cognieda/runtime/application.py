from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.types import PlannerConversationTurn
from cognieda.execution import ExecutorDispatcher

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
        conversation_context = tuple(
            PlannerConversationTurn(
                human_message=turn.human_message,
                planner_message=turn.planner_message,
            )
            for turn in self.session.conversation_history.turns
        )
        planner_output = await self.planner_agent.run(
            message,
            session_frame=self.session.session_frame,
            conversation_context=conversation_context,
        )
        self.session = self.session.advance(
            session_frame=planner_output.session_frame,
            human_message=message,
            planner_message=planner_output.response,
        )

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=planner_output.response,
        )

from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlanningContext
from cognieda.execution import ExecutorDispatcher
from cognieda.schemas.artifacts import SessionFrame

from .conversation import ConversationHistory
from .messages import Message, MessageRole, MessageType
from .workspace import Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        dispatcher: ExecutorDispatcher,
    ) -> None:
        self.workspace = workspace
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher
        self.session_frame = SessionFrame()
        self.conversation_history = ConversationHistory()

    async def submit_message(self, message: str) -> Message:
        planning_context = PlanningContext(
            objective=self.session_frame.objective,
            assumptions=self.session_frame.assumptions,
            tasks=self.session_frame.tasks,
            evidences=self.session_frame.evidences,
            data_profile=self.session_frame.data_profile,
            conversation_history=self.conversation_history,
        )
        planner_output = await self.planner_agent.run(
            message,
            planning_context=planning_context,
            session_frame=self.session_frame,
        )
        self.session_frame = planner_output.session_frame
        if planner_output.new_messages:
            self.conversation_history = self.conversation_history.add_turn(
                planner_output.new_messages
            )

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=planner_output.response,
        )

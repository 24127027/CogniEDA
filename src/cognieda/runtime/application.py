from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlanningContext

from cognieda.execution import ExecutorDispatcher

from .session import SessionFrame
from .messages import Message, MessageRole, MessageType
from .conversation import ConversationHistory
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

        # TODO: build the PlanningContext from the current session state
        # and conversation history
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
            planning_context=planning_context
        )
        if planner_output.new_messages:
            self.conversation_history = self.conversation_history.add_turn(
                planner_output.new_messages
            )
            self.session_frame.conversation = self.conversation_history
        if planner_output.error:
            content = f"Planner error: {planner_output.error}"
        else:
            content = str(planner_output.plan)

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=content,
        )

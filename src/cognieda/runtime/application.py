from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.execution import ExecutorDispatcher

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

    async def submit_message(self, message: str) -> Message:
        planner_output = await self.planner_agent.run(message)

        if planner_output.error:
            content = f"Planner error: {planner_output.error}"
        else:
            content = str(planner_output.plan)

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=content,
        )

from __future__ import annotations

from .workspace import Workspace
from .messages import Message, MessageType, MessageRole

from ..agents.planner.agent import Planner
from ..agents.planner.types import PlannerOutput


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        dispatcher: object | None = None,
    ) -> None:
        self.workspace = workspace
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher

    async def start_session(self) -> None:
        print(f"Workspace: {self.workspace.root}")
        print("Session started.")

    async def submit_message(self, message: str) -> Message:
        result = await self.planner_agent.run(message)

        planner_output = PlannerOutput.model_validate(result.payload)

        if planner_output.error:
            content = f"Planner error: {planner_output.error}"
        else:
            content = str(planner_output.plan)

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=content,
        )
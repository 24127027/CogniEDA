# src/runtime/application.py

from __future__ import annotations

from .workspace import Workspace
from .messages import Message, MessageType, MessageRole


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: object,
        dispatcher: object,
    ):
        self.workspace = workspace
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher

    async def start_session(self) -> None:
        print(f"Workspace: {self.workspace.root}")
        print("Session started.")

    async def submit_message(self, message: str) -> Message:
        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=f"Mock response to: {message}",
        )
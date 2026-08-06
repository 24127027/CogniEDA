from __future__ import annotations

from .workspace import Workspace


class Application:
    def __init__(self, 
                 workspace: Workspace, 
                 planner_agent: object,
                 dispatcher: object):

        self.workspace = workspace
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher

    async def start_session(self) -> None:
        """Start a new session."""
        # Implementation for starting a session
        pass

    async def resume_session(self) -> None:
        """Load an existing session with the given session ID."""
        # Implementation for loading a session
        pass

    async def submit_message(self, message: str) -> None:
        """Submit a message to the session with the given session ID."""
        # Implementation for submitting a message
        pass
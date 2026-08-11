from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlanningContext
from cognieda.execution import ExecutorDispatcher
from cognieda.schemas.artifacts import SessionFrame
from cognieda.application.ports import AgentFactoryPort

from .conversation import ConversationHistory
from .messages import Message, MessageRole, MessageType
from .workspace import Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        dispatcher: ExecutorDispatcher,
        agent_factory: AgentFactoryPort
    ) -> None:
        self.workspace = workspace
        self.agent_factory = agent_factory
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher
        self.agent_factory = agent_factory
        self.session_frame = SessionFrame()
        self.conversation_history = ConversationHistory()

    async def submit_message(self, message: str) -> Message:
        if message.startswith("/"):
            return await self._handle_command(message)
        
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

    # TODO: Move command handling to a separate class or module for better separation of concerns
    async def _handle_command(self, command: str) -> Message:
        parts = command.split()

        match parts:
            #
            # Register a skill in skills.toml
            #
            case ["/skill", "register", name, directory]:
                self.workspace.add_skill(name, directory)
                return self._text(
                    f"Registered skill '{name}' at '{directory}'."
                )

            case ["/skill", "unregister", name]:
                self.workspace.remove_skill(name)
                return self._text(
                    f"Unregistered skill '{name}'."
                )

            #
            # Assign a skill to a worker in agents.toml
            #
            case ["/skill", "assign", worker, skill]:
                self.workspace.add_worker_skill(worker, skill)
                self.agent_factory.reload_tooling()  # Reload the tooling to reflect the updated skills
                await self.planner_agent.reload_model()

                return self._text(
                    f"Assigned skill '{skill}' to '{worker}'."
                )

            case ["/skill", "unassign", worker, skill]:
                self.workspace.remove_worker_skill(worker, skill)
                self.agent_factory.reload_tooling()  # Reload the tooling to reflect the updated skills
                await self.planner_agent.reload_model()

                return self._text(
                    f"Removed skill '{skill}' from '{worker}'."
                )

            case _:
                return self._text(
                    f"Unknown command: '{command}'."
                )

    def _text(self, content: str) -> Message:
        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=content,
        )
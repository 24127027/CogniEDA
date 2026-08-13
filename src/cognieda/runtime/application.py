from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.application.ports import AgentFactoryPort
from cognieda.execution import ExecutorDispatcher
from cognieda.schemas.artifacts import SessionFrame

from .conversation import ConversationHistory
from .messages import Message, MessageRole, MessageType
from .planner_context import apply_planner_output, build_planning_context
from .workspace import Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        dispatcher: ExecutorDispatcher,
        agent_factory: AgentFactoryPort,
    ) -> None:
        self.workspace = workspace
        self.agent_factory = agent_factory
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher
        self.session_frame = SessionFrame()
        self.conversation_history = ConversationHistory()

    async def submit_message(self, message: str) -> Message:
        if message.startswith("/"):
            return await self._handle_command(message)

        planning_context = build_planning_context(
            self.session_frame,
            self.conversation_history,
        )
        planner_output = await self.planner_agent.run(
            message,
            planning_context=planning_context,
        )
        self.session_frame = apply_planner_output(self.session_frame, planner_output)
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
            case ["/skill", "add", name, directory]:
                self.workspace.add_skill(name, directory)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )
                return self._text(f"Added skill '{name}'.")

            case ["/skill", "rm", name]:
                self.workspace.remove_skill(name)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )
                return self._text(f"Removed skill '{name}'.")

            case ["/skill", "use", worker, skill]:
                self.workspace.add_worker_skill(worker, skill)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )
                return self._text(
                    f"Assigned '{skill}' to '{worker}'."
                )

            case ["/skill", "drop", worker, skill]:
                self.workspace.remove_worker_skill(worker, skill)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )
                return self._text(
                    f"Removed '{skill}' from '{worker}'."
                )

            case ["/reload", "instruction"]:
                await self._reload_runtime(
                    reload_instruction=True,
                )
                return self._text(
                    "Planner instructions reloaded."
                )

            case ["/provider", "use", profile]:
                self.workspace.use_provider(profile)

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(
                    f"Using provider '{profile}'."
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
    
    async def _reload_runtime(
        self,
        *,
        reload_tooling: bool = False,
        reload_instruction: bool = False,
        recreate_agent: bool = False,
    ) -> None:
        if reload_tooling:
            self.agent_factory.reload_tooling()

        await self.planner_agent.reload(
            model_config=self.workspace.model_config,
            agent_instruction=(
                self.workspace.load_agent_instruction()
                if reload_instruction
                else None
            ),
            recreate_agent=recreate_agent,
        )
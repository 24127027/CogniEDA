from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.application.ports import AgentFactoryPort
from cognieda.execution import ExecutorDispatcher
from cognieda.schemas.artifacts import SessionFrame

from .conversation import ConversationHistory
from .messages import Message, MessageRole, MessageType
from .planner_context import apply_planner_output, build_planner_context
from .workspace import Workspace, MissingModelCredentialError


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

        planner_context = build_planner_context(self.session_frame)
        try:
            planner_output = await self.planner_agent.run(
                message,
                planner_context=planner_context,
                conversation_history=self.conversation_history,
            )
        except MissingModelCredentialError as e:
            return self._text(
                f"{e}\n\n"
                "Run '/provider key <provider>' to configure an API key."
            )

        self.session_frame = apply_planner_output(
            self.session_frame,
            planner_output,
            request=message,
        )
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
            # Skills
            #
            case ["/skill", "add", name, directory]:
                self.workspace.add_skill(name, directory)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(
                    f"Added skill '{name}'."
                )

            case ["/skill", "rm", name]:
                self.workspace.remove_skill(name)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(
                    f"Removed skill '{name}'."
                )

            case ["/skill", "list"]:
                skills = self.workspace.load_skills_config()

                if not skills:
                    return self._text("No skills registered.")

                return self._text(
                    "\n".join(
                        f"{name}: {cfg['directories']}"
                        for name, cfg in skills.items()
                    )
                )

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

            #
            # Providers
            #
            case ["/provider"]:
                profile = self.workspace.project_config.default_provider

                try:
                    self.workspace.project_config.validate()
                except ValueError as e:
                    return self._text(str(e))
                provider = self.workspace.project_config.providers[profile]

                configured = "yes" if provider.api_key_configured() else "no"

                return self._text(
                    f"""Current provider : {profile}
        Model            : {provider.model}
        API key          : {configured}"""
                )

            case ["/provider", "list"]:
                return self._text(
                    "\n".join(
                        self.workspace.project_config.providers.keys()
                    )
                )

            case ["/provider", "use", profile]:
                self.workspace.use_provider(profile)

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(
                    f"Using provider '{profile}'."
                )

            case ["/provider", "model", profile, model]:
                self.workspace.set_provider_model(
                    profile,
                    model,
                )

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(
                    f"Updated '{profile}' model to '{model}'."
                )
            # TODO:
            # Prompting for secrets belongs to the CLI/UI layer.
            # Application should receive the API key as an argument rather than
            # calling input() directly.
            case ["/provider", "key", profile]:
                api_key = input(
                    f"{profile} API key: "
                ).strip()

                self.workspace.set_provider_api_key(
                    profile,
                    api_key,
                )

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(
                    f"Stored API key for '{profile}'."
                )

            #
            # Planner
            #
            case ["/reload"]:
                await self._reload_runtime(
                    reload_instruction=True,
                )

                return self._text(
                    "Planner instructions reloaded."
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
            model_config=(
                self.workspace.project_config.try_resolve_model()
                if recreate_agent
                else None
            ),
            agent_instruction=(
                self.workspace.load_agent_instruction()
                if reload_instruction
                else None
            ),
            recreate_agent=recreate_agent,
        )

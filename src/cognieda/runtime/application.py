from __future__ import annotations

from collections.abc import AsyncIterator

from cognieda.agents.planner.agent import Planner
from cognieda.application.ports import AgentFactoryPort
from cognieda.execution import ExecutorDispatcher
from cognieda.schemas.artifacts import SessionFrame

from .conversation import ConversationHistory
from .messages import ErrorEvent, MarkdownEvent, StatusEvent, UIEvent
from .planner_context import apply_planner_output, build_planning_context
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

    async def submit_message(self, message: str) -> AsyncIterator[UIEvent]:
        if message.startswith("/"):
            async for event in self._handle_command(message):
                yield event
            return

        yield StatusEvent("Planning...")

        planning_context = build_planning_context(
            self.session_frame,
            self.conversation_history,
        )
        try:
            planner_output = await self.planner_agent.run(
                message,
                planning_context=planning_context,
            )
        except MissingModelCredentialError as e:
            yield ErrorEvent(
                f"{e}\n\n"
                "Run '/provider key <provider>' to configure an API key."
            )
            return

        self.session_frame = apply_planner_output(self.session_frame, planner_output)
        if planner_output.new_messages:
            self.conversation_history = self.conversation_history.add_turn(
                planner_output.new_messages
            )

        if planner_output.error is not None:
            yield ErrorEvent(content=planner_output.response)
            return

        yield MarkdownEvent(content=planner_output.response)

    # TODO: Move command handling to a separate class or module for better separation of concerns
    async def _handle_command(self, command: str) -> AsyncIterator[UIEvent]:
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

                yield MarkdownEvent(f"Added skill '{name}'.")

            case ["/skill", "rm", name]:
                self.workspace.remove_skill(name)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                yield MarkdownEvent(f"Removed skill '{name}'.")

            case ["/skill", "list"]:
                skills = self.workspace.load_skills_config()

                if not skills:
                    yield MarkdownEvent("No skills registered.")
                    return

                yield MarkdownEvent(
                    "\n".join(
                        f"{name}: {cfg['directories']}"
                        for name, cfg in skills.items()
                    )
                )

            case ["/skill", "use", worker, skill] | ["/skill", "assign", worker, skill]:
                self.workspace.add_worker_skill(worker, skill)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                yield MarkdownEvent(f"Assigned '{skill}' to '{worker}'.")

            case ["/skill", "drop", worker, skill] | ["/skill", "remove", worker, skill]:
                self.workspace.remove_worker_skill(worker, skill)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                yield MarkdownEvent(f"Removed '{skill}' from '{worker}'.")

            #
            # Providers
            #
            case ["/provider"]:
                profile = self.workspace.project_config.default_provider

                try:
                    self.workspace.project_config.validate()
                except ValueError as e:
                    yield MarkdownEvent(str(e))
                    return
                provider = self.workspace.project_config.providers[profile]

                configured = "yes" if provider.api_key_configured() else "no"

                yield MarkdownEvent(
                    f"""Current provider : {profile}
        Model            : {provider.model}
        API key          : {configured}"""
                )

            case ["/provider", "list"]:
                yield MarkdownEvent(
                    "\n".join(
                        self.workspace.project_config.providers.keys()
                    )
                )

            case ["/provider", "use", profile]:
                self.workspace.use_provider(profile)

                await self._reload_runtime(
                    recreate_agent=True,
                )

                yield MarkdownEvent(f"Using provider '{profile}'.")

            case ["/provider", "model", profile, model]:
                self.workspace.set_provider_model(
                    profile,
                    model,
                )

                await self._reload_runtime(
                    recreate_agent=True,
                )

                yield MarkdownEvent(f"Updated '{profile}' model to '{model}'.")
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

                yield MarkdownEvent(f"Stored API key for '{profile}'.")

            #
            # Planner
            #
            case ["/reload"]:
                await self._reload_runtime(
                    reload_instruction=True,
                )

                yield MarkdownEvent("Planner instructions reloaded.")

            case _:
                yield ErrorEvent(f"Unknown command: '{command}'.")
    
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
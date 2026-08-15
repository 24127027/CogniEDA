from __future__ import annotations

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.state import PlannerTurnOutcome
from cognieda.application.ports import AgentFactoryPort
from cognieda.infrastructure.persistence.repositories import SessionFrameRepository
from cognieda.runtime.event_bus import EventBus
from cognieda.runtime.events import HumanInputRequested, MessageProduced, PlanProposed
from cognieda.schemas.artifacts import SessionFrame

from .messages import Message, MessageRole, MessageType
from .workspace import MissingModelCredentialError, Workspace


class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        agent_factory: AgentFactoryPort,
        event_bus: EventBus,
        session_frames: SessionFrameRepository,
    ) -> None:
        self.workspace = workspace
        self.agent_factory = agent_factory
        self.planner_agent = planner_agent
        self.event_bus = event_bus
        self._session_frames = session_frames

    @property
    def session_frame(self) -> SessionFrame:
        return self._session_frames.get_current()

    @session_frame.setter
    def session_frame(self, value: SessionFrame) -> None:
        self._session_frames.save_current(value)

    async def submit_message(self, message: str) -> None:
        if message.startswith("/"):
            command_result = await self._handle_command(message)
            self.event_bus.publish(MessageProduced(message=command_result))
            return

        try:
            outcome = await self.planner_agent.handle_message(message)
        except MissingModelCredentialError as e:
            self._emit_message(f"{e}\n\nRun '/provider key <provider>' to configure an API key.")
            return

        self._emit_planner_outcome(outcome)

    def _emit_planner_outcome(self, outcome: PlannerTurnOutcome) -> None:
        if outcome.error is not None:
            self._emit_message(outcome.error.message, message_type=MessageType.ERROR)
            return

        if outcome.proposed_plan is not None:
            self.event_bus.publish(PlanProposed(plan=outcome.proposed_plan))

        if outcome.response is not None:
            self._emit_message(outcome.response)

        if outcome.human_input_request is not None:
            self.event_bus.publish(
                HumanInputRequested(
                    message=Message(
                        type=MessageType.TEXT,
                        role=MessageRole.ASSISTANT,
                        content=outcome.human_input_request,
                    )
                )
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

                return self._text(f"Added skill '{name}'.")

            case ["/skill", "rm", name]:
                self.workspace.remove_skill(name)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(f"Removed skill '{name}'.")

            case ["/skill", "list"]:
                skills = self.workspace.load_skills_config()

                if not skills:
                    return self._text("No skills registered.")

                return self._text(
                    "\n".join(f"{name}: {cfg['directories']}" for name, cfg in skills.items())
                )

            case ["/skill", "use", worker, skill]:
                self.workspace.add_worker_skill(worker, skill)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(f"Assigned '{skill}' to '{worker}'.")

            case ["/skill", "drop", worker, skill]:
                self.workspace.remove_worker_skill(worker, skill)

                await self._reload_runtime(
                    reload_tooling=True,
                    recreate_agent=True,
                )

                return self._text(f"Removed '{skill}' from '{worker}'.")

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
                return self._text("\n".join(self.workspace.project_config.providers.keys()))

            case ["/provider", "use", profile]:
                self.workspace.use_provider(profile)

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(f"Using provider '{profile}'.")

            case ["/provider", "model", profile, model]:
                self.workspace.set_provider_model(
                    profile,
                    model,
                )

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(f"Updated '{profile}' model to '{model}'.")
            # TODO:
            # Prompting for secrets belongs to the CLI/UI layer.
            # Application should receive the API key as an argument rather than
            # calling input() directly.
            case ["/provider", "key", profile]:
                api_key = input(f"{profile} API key: ").strip()

                self.workspace.set_provider_api_key(
                    profile,
                    api_key,
                )

                await self._reload_runtime(
                    recreate_agent=True,
                )

                return self._text(f"Stored API key for '{profile}'.")

            #
            # Planner
            #
            case ["/reload"]:
                await self._reload_runtime(
                    reload_instruction=True,
                )

                return self._text("Planner instructions reloaded.")

            case _:
                return self._text(f"Unknown command: '{command}'.")

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
                self.workspace.project_config.try_resolve_model() if recreate_agent else None
            ),
            agent_instruction=(
                self.workspace.load_agent_instruction() if reload_instruction else None
            ),
            recreate_agent=recreate_agent,
        )

    def _emit_message(
        self,
        content: str,
        *,
        message_type: MessageType = MessageType.TEXT,
    ) -> None:
        self.event_bus.publish(
            MessageProduced(
                message=Message(
                    type=message_type,
                    role=MessageRole.ASSISTANT,
                    content=content,
                )
            )
        )

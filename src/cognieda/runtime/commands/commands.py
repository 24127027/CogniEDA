from __future__ import annotations

from cognieda.runtime.messages import Message, MessageRole, MessageType

from .base import CommandContext, ResolvedCommand


def text(content: str) -> Message:
    return Message(
        type=MessageType.TEXT,
        role=MessageRole.SYSTEM,
        content=content,
    )


class SkillAddCommand:
    name = "skill.add"
    description = "Add a skill to the workspace."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if len(command.args) != 2:
            return text("Usage: /skill.add <name> <directory>")

        name, directory = command.args

        context.workspace.add_skill(name, directory)

        await context.reload_runtime(
            reload_tooling=True,
            recreate_agent=True,
        )

        return text(f"Added skill '{name}'.")


class SkillRemoveCommand:
    name = "skill.rm"
    description = "Remove a skill from the workspace."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if len(command.args) != 1:
            return text("Usage: /skill.rm <name>")

        name = command.args[0]

        context.workspace.remove_skill(name)

        await context.reload_runtime(
            reload_tooling=True,
            recreate_agent=True,
        )

        return text(f"Removed skill '{name}'.")


class SkillListCommand:
    name = "skill.list"
    description = "List all registered skills."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if command.args:
            return text("Usage: /skill.list")

        skills = context.workspace.load_skills_config()

        if not skills:
            return text("No skills registered.")

        return text(
            "\n".join(
                f"{name}: {cfg['directories']}"
                for name, cfg in skills.items()
            )
        )


class SkillUseCommand:
    name = "skill.use"
    description = "Assign a skill to a worker."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if len(command.args) != 2:
            return text("Usage: /skill.use <worker> <skill>")

        worker, skill = command.args

        context.workspace.add_worker_skill(worker, skill)

        await context.reload_runtime(
            reload_tooling=True,
            recreate_agent=True,
        )

        return text(f"Assigned '{skill}' to '{worker}'.")


class SkillDropCommand:
    name = "skill.drop"
    description = "Remove a skill from a worker."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if len(command.args) != 2:
            return text("Usage: /skill.drop <worker> <skill>")

        worker, skill = command.args

        context.workspace.remove_worker_skill(worker, skill)

        await context.reload_runtime(
            reload_tooling=True,
            recreate_agent=True,
        )

        return text(f"Removed '{skill}' from '{worker}'.")


class ProviderStatusCommand:
    name = "provider"
    description = "Display the status of the current provider."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if command.args:
            return text("Usage: /provider")

        profile = context.workspace.project_config.default_provider

        try:
            context.workspace.project_config.validate()
        except ValueError as e:
            return text(str(e))

        provider = context.workspace.project_config.providers[profile]

        configured = "yes" if provider.api_key_configured() else "no"

        return text(
            f"""Current provider : {profile}
Model            : {provider.model}
API key          : {configured}"""
        )


class ProviderListCommand:
    name = "provider.list"
    description = "List all configured providers."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if command.args:
            return text("Usage: /provider.list")

        return text(
            "\n".join(
                context.workspace.project_config.providers.keys()
            )
        )


class ProviderUseCommand:
    name = "provider.use"
    description = "Switch to a different provider."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if len(command.args) != 1:
            return text("Usage: /provider.use <profile>")

        profile = command.args[0]

        context.workspace.use_provider(profile)

        await context.reload_runtime(
            recreate_agent=True,
        )

        return text(f"Using provider '{profile}'.")


class ProviderModelCommand:
    name = "provider.model"
    description = "Set the model for a provider."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if len(command.args) != 2:
            return text("Usage: /provider.model <profile> <model>")

        profile, model = command.args

        context.workspace.set_provider_model(
            profile,
            model,
        )

        await context.reload_runtime(
            recreate_agent=True,
        )

        return text(
            f"Updated '{profile}' model to '{model}'."
        )


class ProviderKeyCommand:
    name = "provider.key"
    description = "Set the API key for a provider."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if len(command.args) != 1:
            return text("Usage: /provider.key <profile>")

        profile = command.args[0]

        api_key = context.prompt_secret(
            f"{profile} API key: "
        ).strip()

        context.workspace.set_provider_api_key(
            profile,
            api_key,
        )

        await context.reload_runtime(
            recreate_agent=True,
        )

        return text(
            f"Stored API key for '{profile}'."
        )


class ReloadCommand:
    name = "reload"
    description = "Reload the planner instructions."

    async def execute(
        self,
        command: ResolvedCommand,
        context: CommandContext,
    ) -> Message:
        if command.args:
            return text("Usage: /reload")

        await context.reload_runtime(
            reload_instruction=True,
        )

        return text("Planner instructions reloaded.")
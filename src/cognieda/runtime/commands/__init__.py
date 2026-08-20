from .base import CommandContext, ParsedCommand
from .commands import (
    ProviderConfigCommand,
    ProviderListCommand,
    ProviderModelCommand,
    ProviderStatusCommand,
    ProviderUseCommand,
    ReloadCommand,
    SkillAddCommand,
    SkillDropCommand,
    SkillListCommand,
    SkillRemoveCommand,
    SkillUseCommand,
)
from .handler import CommandHandler
from .parser import CommandParser
from .registry import CommandRegistry


def create_command_registry() -> CommandRegistry:
    return CommandRegistry(
        commands=(
            SkillAddCommand(),
            SkillRemoveCommand(),
            SkillListCommand(),
            SkillUseCommand(),
            SkillDropCommand(),
            ProviderStatusCommand(),
            ProviderListCommand(),
            ProviderUseCommand(),
            ProviderModelCommand(),
            ProviderConfigCommand(),
            ReloadCommand(),
        )
    )


__all__ = [
    "CommandContext",
    "ParsedCommand",
    "CommandHandler",
    "CommandParser",
    "CommandRegistry",
    "create_command_registry",
]
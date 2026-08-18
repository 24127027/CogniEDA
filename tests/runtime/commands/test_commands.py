from cognieda.runtime.commands import (
    CommandParser,
    ProviderStatusCommand,
    ProviderUseCommand,
    SkillAddCommand,
    SkillListCommand,
    SkillRemoveCommand,
)
from cognieda.runtime.commands.base import ResolvedCommand
from cognieda.runtime.commands.registry import CommandRegistry


def test_parser_preserves_tokens() -> None:
    parser = CommandParser()

    result = parser.parse(
        "/skill add test_skill ./skills/test"
    )

    assert result.tokens == (
        "/skill",
        "add",
        "test_skill",
        "./skills/test",
    )


def test_registry_resolves_nested_command() -> None:
    registry = CommandRegistry(
        commands=[
            SkillAddCommand(),
            SkillListCommand(),
        ]
    )

    result = registry.resolve(
        (
            "/skill",
            "add",
            "test_skill",
            "./skills/test",
        )
    )

    assert result == ResolvedCommand(
        name="skill.add",
        args=(
            "test_skill",
            "./skills/test",
        ),
    )


def test_registry_suggests_commands() -> None:
    registry = CommandRegistry(
        commands=[
            SkillAddCommand(),
            SkillRemoveCommand(),
            SkillListCommand(),
            ProviderStatusCommand(),
            ProviderUseCommand(),
        ]
    )

    result = registry.suggest("/skill")

    assert [command.name for command in result] == [
        "skill.add",
        "skill.rm",
        "skill.list",
    ]

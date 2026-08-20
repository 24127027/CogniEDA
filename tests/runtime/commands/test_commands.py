import asyncio
from unittest.mock import AsyncMock, Mock

from cognieda.runtime.commands import (
    CommandParser,
    ProviderStatusCommand,
    ProviderUseCommand,
    SkillAddCommand,
    SkillListCommand,
    SkillRemoveCommand,
)
from cognieda.runtime.commands.base import CommandContext, ResolvedCommand
from cognieda.runtime.commands.commands import ProviderConfigCommand
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


def test_provider_config_prompts_for_profile_when_missing() -> None:
    workspace = Mock()
    prompt = Mock(side_effect=["openai", "gpt-5"])
    prompt_secret = Mock(return_value="secret")
    reload_runtime = AsyncMock()

    context = CommandContext(
        workspace=workspace,
        agent_factory=Mock(),
        planner=Mock(),
        reload_runtime=reload_runtime,
        prompt=prompt,
        prompt_secret=prompt_secret,
    )

    command = ResolvedCommand(name="provider.config", args=())

    result = asyncio.run(
        ProviderConfigCommand().execute(command, context)
    )

    assert result.content == (
        "Configured provider 'openai' with model 'gpt-5'."
    )
    workspace.use_provider.assert_called_once_with("openai")
    workspace.set_provider_model.assert_called_once_with(
        "openai",
        "gpt-5",
    )
    workspace.set_provider_api_key.assert_called_once_with(
        "openai",
        "secret",
    )
    reload_runtime.assert_awaited_once_with(recreate_agent=True)
    prompt.assert_any_call("Provider profile: ")
    prompt.assert_any_call("openai model: ")
    prompt_secret.assert_called_once_with("openai API key: ")


def test_provider_config_uses_arg_profile_without_profile_prompt() -> None:
    workspace = Mock()
    prompt = Mock(return_value="gpt-5-mini")
    prompt_secret = Mock(return_value="secret")
    reload_runtime = AsyncMock()

    context = CommandContext(
        workspace=workspace,
        agent_factory=Mock(),
        planner=Mock(),
        reload_runtime=reload_runtime,
        prompt=prompt,
        prompt_secret=prompt_secret,
    )

    command = ResolvedCommand(
        name="provider.config",
        args=("openai",),
    )

    result = asyncio.run(
        ProviderConfigCommand().execute(command, context)
    )

    assert result.content == (
        "Configured provider 'openai' with model 'gpt-5-mini'."
    )
    prompt.assert_called_once_with("openai model: ")
    prompt_secret.assert_called_once_with("openai API key: ")

from __future__ import annotations

from collections.abc import Iterable

from .base import Command, ResolvedCommand


class CommandNotFoundError(Exception):
    pass


class CommandRegistry:
    def __init__(self, commands: Iterable[Command] = ()) -> None:
        self._commands: dict[str, Command] = {}

        for command in commands:
            self.register(command)

    def register(self, command: Command) -> None:
        if command.name in self._commands:
            raise ValueError(
                f"Command already registered: {command.name}"
            )

        self._commands[command.name] = command

    def resolve(self, tokens: tuple[str, ...]) -> ResolvedCommand:
        if not tokens:
            raise CommandNotFoundError("Empty command.")

        if not tokens[0].startswith("/"):
            raise CommandNotFoundError("Not a command.")

        parts = [tokens[0][1:], *tokens[1:]]

        # Find the longest registered command name.
        #
        # Example:
        #
        # /skill add foo ./skills/foo
        #
        # candidates:
        #   skill.add.foo
        #   skill.add
        #   skill
        #
        # "skill.add" wins.
        for length in range(len(parts), 0, -1):
            name = ".".join(parts[:length])

            if name in self._commands:
                return ResolvedCommand(
                    name=name,
                    args=tuple(parts[length:]),
                )

        raise CommandNotFoundError(
            f"Unknown command: '{' '.join(tokens)}'."
        )

    def get(self, name: str) -> Command:
        try:
            return self._commands[name]
        except KeyError:
            raise CommandNotFoundError(
                f"Unknown command: '/{name.replace('.', ' ')}'."
            ) from None

    def commands(self) -> tuple[Command, ...]:
        return tuple(self._commands.values())

    def suggest(self, prefix: str) -> tuple[Command, ...]:
        normalized = prefix.removeprefix("/")

        return tuple(
            command
            for name, command in self._commands.items()
            if name.startswith(normalized)
        )
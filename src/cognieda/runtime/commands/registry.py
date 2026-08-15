from __future__ import annotations

from collections.abc import Iterable

from .base import Command


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

    def resolve(self, name: str) -> Command:
        try:
            return self._commands[name]
        except KeyError:
            raise CommandNotFoundError(
                f"Unknown command: '/{name.replace('.', ' ')}'."
            ) from None

    def commands(self) -> tuple[Command, ...]:
        return tuple(self._commands.values())

    def suggest(self, prefix: str) -> tuple[Command, ...]:
        """
        Used later by CLI/TUI autocomplete.

        Example:
            suggest("skill")
            suggest("skill.")
        """
        normalized = prefix.removeprefix("/")

        return tuple(
            command
            for name, command in self._commands.items()
            if name.startswith(normalized)
        )
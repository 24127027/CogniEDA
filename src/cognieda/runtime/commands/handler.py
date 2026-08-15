from __future__ import annotations

from .base import CommandContext
from .parser import CommandParser
from .registry import CommandNotFoundError, CommandRegistry


class CommandHandler:
    def __init__(
        self,
        parser: CommandParser,
        registry: CommandRegistry,
        context: CommandContext,
    ) -> None:
        self._parser = parser
        self._registry = registry
        self._context = context

    async def handle(self, input_text: str):
        try:
            parsed = self._parser.parse(input_text)
        except ValueError as e:
            return self._error(str(e))

        try:
            command = self._registry.resolve(parsed.name)
        except CommandNotFoundError as e:
            return self._error(str(e))

        return await command.execute(
            parsed,
            self._context,
        )

    @staticmethod
    def _error(message: str):
        from cognieda.runtime.messages import (
            Message,
            MessageRole,
            MessageType,
        )

        return Message(
            type=MessageType.TEXT,
            role=MessageRole.SYSTEM,
            content=message,
        )
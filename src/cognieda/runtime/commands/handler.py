from __future__ import annotations

from cognieda.runtime.messages import (
    Message,
    MessageRole,
    MessageType,
)

from .base import CommandContext
from .parser import CommandParser
from .registry import CommandNotFoundError, CommandRegistry
from .types import CommandSuggestion

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

    async def handle(self, input_text: str) -> Message:
        try:
            parsed = self._parser.parse(input_text)
            resolved = self._registry.resolve(parsed.tokens)
        except (ValueError, CommandNotFoundError) as e:
            return self._error(str(e))

        command = self._registry.get(resolved.name)

        return await command.execute(
            resolved,
            self._context,
        )

    def suggest(
        self,
        prefix: str,
    ) -> tuple[CommandSuggestion, ...]:
        return self._registry.suggest(prefix)

    @staticmethod
    def _error(message: str) -> Message:
        return Message(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=message,
        )
    
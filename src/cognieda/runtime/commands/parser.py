from __future__ import annotations

import shlex

from .base import ParsedCommand


class CommandParser:
    def parse(self, input_text: str) -> ParsedCommand:
        parts = shlex.split(input_text)

        if not parts:
            raise ValueError("Empty command.")

        if not parts[0].startswith("/"):
            raise ValueError("Not a command.")

        return ParsedCommand(
            tokens=tuple(parts),
        )
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

        command_parts = [parts[0][1:]]
        args = list(parts[1:])

        # Try to identify hierarchical commands.
        #
        # /skill add foo
        # -> skill.add + foo
        #
        # /provider use openai
        # -> provider.use + openai
        #
        # The registry decides whether the second token is actually
        # part of the command name.

        if args:
            command_parts.append(args.pop(0))

        return ParsedCommand(
            name=".".join(command_parts),
            args=tuple(args),
        )
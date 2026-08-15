from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.shortcuts import PromptSession

from cognieda.runtime.commands.types import CommandSuggestion

if TYPE_CHECKING:
    from cognieda.runtime import Application


class CommandCompleter(Completer):
    """Provides slash-command completions from the Application."""

    def __init__(self, application: Application) -> None:
        self.application = application

    def get_completions(
        self,
        document: Document,
        complete_event,
    ):
        text = document.text

        # Only activate completion for slash commands.
        if not text.startswith("/"):
            return

        # Do not suggest while entering command arguments.
        #
        # Examples:
        #   "/ski"          -> suggestions
        #   "/skill"        -> suggestions
        #   "/skill "       -> suggestions for subcommands
        #   "/skill add "   -> no suggestions
        if text.count(" ") > 1:
            return

        suggestions = self._suggestions(text)

        for suggestion in suggestions:
            yield Completion(
                suggestion.name,
                start_position=-len(text),
                display=suggestion.name,
                display_meta=suggestion.description,
            )

    def _suggestions(
        self,
        text: str,
    ) -> tuple[CommandSuggestion, ...]:
        return self.application.suggest_commands(text)


class Prompt:
    """Interactive terminal prompt.

    The prompt owns terminal interaction only. It does not know about
    CommandRegistry or command implementations.
    """

    def __init__(
        self,
        application: Application,
        *,
        prompt: str = "> ",
    ) -> None:
        self.application = application

        self._session: PromptSession[str] = PromptSession(
            history=InMemoryHistory(),
            completer=CommandCompleter(application),
            complete_while_typing=True,
        )

        self._prompt = prompt

    async def read(self) -> str:
        """Read one submitted line from the user."""
        return await self._session.prompt_async(self._prompt)
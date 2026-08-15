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
    def __init__(self, application: Application) -> None:
        self.application = application

    def get_completions(
        self,
        document: Document,
        complete_event,
    ):
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        for suggestion in self.application.suggest_commands(text):
            yield Completion(
                text=suggestion.name,
                start_position=-len(text),
                display=suggestion.name,
                display_meta=suggestion.description,
            )

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
            self._session = PromptSession(
                history=InMemoryHistory(),
                completer=CommandCompleter(application),
                complete_while_typing=True,
            )
            self._prompt = prompt

    async def read(self) -> str:
        return await self._session.prompt_async(self._prompt)
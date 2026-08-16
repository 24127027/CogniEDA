from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.shortcuts import PromptSession

from rich.console import Console
from rich.control import Control
from rich.segment import ControlType

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
                text=f"/{suggestion.name}",
                start_position=-len(text),
                display=f"/{suggestion.name}",
                display_meta=suggestion.description,
            )
class Prompt:
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
        self._console = Console()

    async def read(self) -> str:
        text = await self._session.prompt_async(self._prompt)
        self._erase_submitted_input()
        return text

    def _erase_submitted_input(self) -> None:
        if not self._console.is_terminal or self._console.is_dumb_terminal:
            return

        self._console.control(
            Control.move(y=-1),
            Control.move_to_column(0),
            Control((ControlType.ERASE_IN_LINE, 2)),
        )
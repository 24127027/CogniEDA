from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import PromptSession


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
        bindings = create_key_bindings()

        self._session = PromptSession(
            history=InMemoryHistory(),
            completer=CommandCompleter(application),
            complete_while_typing=True,
            erase_when_done=True,
            key_bindings=bindings,
            multiline=False,
        )

        self._prompt = prompt

    async def read(self) -> str:
        return await self._session.prompt_async(self._prompt)


def create_key_bindings() -> KeyBindings:
    bindings = KeyBindings()

    @bindings.add("escape", "enter")
    def _(event) -> None:
        event.current_buffer.insert_text("\n")

    return bindings
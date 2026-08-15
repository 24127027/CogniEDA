from __future__ import annotations

import asyncio
from types import SimpleNamespace

from cognieda.cli.main import repl
from cognieda.runtime.messages import MarkdownEvent, StatusEvent


class DummyRenderer:
    def __init__(self) -> None:
        self._inputs = iter(["hello", "quit"])
        self.rendered: list[object] = []

    def render_session_start(self, _workspace_root) -> None:
        return None

    def read_input(self) -> str:
        return next(self._inputs)

    def render_user_message(self, text: str) -> None:
        self.rendered.append(("user", text))

    def render(self, event) -> None:
        self.rendered.append(("event", event))


class DummyApp:
    def __init__(self) -> None:
        self.workspace = SimpleNamespace(root=SimpleNamespace())

    async def submit_message(self, text: str):
        yield StatusEvent("Planning...")
        yield MarkdownEvent(content=f"echo: {text}")


def test_repl_renders_user_input_before_assistant_response() -> None:
    renderer = DummyRenderer()
    app = DummyApp()

    asyncio.run(repl(app, renderer))

    assert len(renderer.rendered) == 3
    first = renderer.rendered[0]
    second = renderer.rendered[1]
    third = renderer.rendered[2]

    assert first == ("user", "hello")
    assert second == ("event", StatusEvent("Planning..."))
    assert third == ("event", MarkdownEvent(content="echo: hello"))

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from cognieda.cli.main import repl
from cognieda.runtime.messages import MessageRole, MessageType


class DummyRenderer:
    def __init__(self) -> None:
        self._inputs = iter(["hello", "quit"])
        self.rendered: list[object] = []

    def render_session_start(self, _workspace_root) -> None:
        return None

    def read_input(self) -> str:
        return next(self._inputs)

    def render(self, message) -> None:
        self.rendered.append(message)


class DummyApp:
    def __init__(self) -> None:
        self.workspace = SimpleNamespace(root=SimpleNamespace())

    async def submit_message(self, text: str):
        return SimpleNamespace(
            type=MessageType.TEXT,
            role=MessageRole.ASSISTANT,
            content=f"echo: {text}",
            model=None,
        )


def test_repl_renders_user_input_before_assistant_response() -> None:
    renderer = DummyRenderer()
    app = DummyApp()

    asyncio.run(repl(app, renderer))

    assert len(renderer.rendered) == 2
    first = renderer.rendered[0]
    second = renderer.rendered[1]

    assert first.role is MessageRole.USER
    assert first.type is MessageType.TEXT
    assert first.content == "hello"

    assert second.role is MessageRole.ASSISTANT
    assert second.type is MessageType.TEXT
    assert second.content == "echo: hello"

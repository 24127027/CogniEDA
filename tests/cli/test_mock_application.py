from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from cognieda.cli.mock_application import MockApplication, run_mock_repl
from cognieda.runtime.messages import MessageRole, MessageType


def test_mock_application_exposes_workspace_root_contract(tmp_path: Path) -> None:
    app = MockApplication(workspace_root=tmp_path)

    assert app.workspace.root == tmp_path.resolve()


def test_submit_message_returns_assistant_text_message() -> None:
    app = MockApplication()

    response = asyncio.run(app.submit_message("hello"))

    assert response.role is MessageRole.ASSISTANT
    assert response.type is MessageType.TEXT
    assert "You said: hello" in str(response.content)


def test_submit_message_supports_error_surface() -> None:
    app = MockApplication()

    response = asyncio.run(app.submit_message("/error broken formatter"))

    assert response.role is MessageRole.ASSISTANT
    assert response.type is MessageType.ERROR
    assert response.content == "broken formatter"


def test_segment_preview_supports_default_and_custom_segments() -> None:
    app = MockApplication()

    default_segments = app.segment_preview("/segments")
    custom_segments = app.segment_preview("/segments first | second | third")

    assert default_segments is not None
    assert len(default_segments) == 3
    assert custom_segments == ("first", "second", "third")


def test_showcase_preview_returns_segments_and_assistant_message() -> None:
    app = MockApplication()

    result = app.showcase_preview("/showcase")

    assert result is not None
    segments, response = result
    assert len(segments) == 3
    assert response.role is MessageRole.ASSISTANT
    assert response.type is MessageType.TEXT
    assert "Showcase Response" in str(response.content)


def test_run_mock_repl_renders_segments_for_segments_command() -> None:
    class DummyRenderer:
        def __init__(self) -> None:
            self._inputs = iter(["/segments", "quit"])
            self.rendered_messages: list[object] = []
            self.rendered_segments: list[tuple[str, ...]] = []

        def render_session_start(self, _workspace_root) -> None:
            return None

        def read_input(self) -> str:
            return next(self._inputs)

        def render(self, message) -> None:
            self.rendered_messages.append(message)

        def render_segments(self, segments) -> None:
            self.rendered_segments.append(tuple(str(segment) for segment in segments))

    app = MockApplication()
    app.workspace = SimpleNamespace(root=Path.cwd().resolve())
    renderer = DummyRenderer()

    asyncio.run(run_mock_repl(app=app, renderer=renderer))

    assert len(renderer.rendered_messages) == 1
    assert renderer.rendered_messages[0].role is MessageRole.USER
    assert len(renderer.rendered_segments) == 1
    assert len(renderer.rendered_segments[0]) == 3


def test_run_mock_repl_showcase_renders_segments_and_assistant() -> None:
    class DummyRenderer:
        def __init__(self) -> None:
            self._inputs = iter(["/showcase", "quit"])
            self.rendered_messages: list[object] = []
            self.rendered_segments: list[tuple[str, ...]] = []

        def render_session_start(self, _workspace_root) -> None:
            return None

        def read_input(self) -> str:
            return next(self._inputs)

        def render(self, message) -> None:
            self.rendered_messages.append(message)

        def render_segments(self, segments) -> None:
            self.rendered_segments.append(tuple(str(segment) for segment in segments))

    app = MockApplication()
    app.workspace = SimpleNamespace(root=Path.cwd().resolve())
    renderer = DummyRenderer()

    asyncio.run(run_mock_repl(app=app, renderer=renderer))

    assert len(renderer.rendered_messages) == 2
    assert renderer.rendered_messages[0].role is MessageRole.USER
    assert renderer.rendered_messages[1].role is MessageRole.ASSISTANT
    assert len(renderer.rendered_segments) == 1
    assert len(renderer.rendered_segments[0]) == 3

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from cognieda.cli.mock_application import MockApplication, run_mock_repl
from cognieda.runtime.messages import ErrorEvent, MarkdownEvent, StatusEvent


def test_mock_application_exposes_workspace_root_contract(tmp_path: Path) -> None:
    app = MockApplication(workspace_root=tmp_path)

    assert app.workspace.root == tmp_path.resolve()


def test_submit_message_emits_status_then_markdown() -> None:
    app = MockApplication()

    async def collect() -> list[object]:
        return [event async for event in app.submit_message("hello")]

    events = asyncio.run(collect())

    assert len(events) == 2
    assert isinstance(events[0], StatusEvent)
    assert events[0].content == "Planning..."
    assert isinstance(events[1], MarkdownEvent)
    assert "You said: hello" in events[1].content


def test_submit_message_supports_error_surface() -> None:
    app = MockApplication()

    async def collect() -> list[object]:
        return [event async for event in app.submit_message("/error broken formatter")]

    events = asyncio.run(collect())

    assert len(events) == 1
    assert isinstance(events[0], ErrorEvent)
    assert events[0].content == "broken formatter"


def test_segment_preview_supports_default_and_custom_segments() -> None:
    app = MockApplication()

    default_segments = app.segment_preview("/segments")
    custom_segments = app.segment_preview("/segments first | second | third")

    assert default_segments is not None
    assert len(default_segments) == 3
    assert custom_segments == ("first", "second", "third")


def test_showcase_preview_returns_segments_and_markdown_event() -> None:
    app = MockApplication()

    result = app.showcase_preview("/showcase")

    assert result is not None
    segments, response = result
    assert len(segments) == 3
    assert isinstance(response, MarkdownEvent)
    assert "Showcase Response" in response.content


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

        def render_user_message(self, message) -> None:
            self.rendered_messages.append(("user", message))

        def render(self, event) -> None:
            self.rendered_messages.append(("event", event))

        def render_segments(self, segments) -> None:
            self.rendered_segments.append(tuple(str(segment) for segment in segments))

    app = MockApplication()
    app.workspace = SimpleNamespace(root=Path.cwd().resolve())
    renderer = DummyRenderer()

    asyncio.run(run_mock_repl(app=app, renderer=renderer))

    assert len(renderer.rendered_messages) == 1
    assert renderer.rendered_messages[0][0] == "user"
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

        def render_user_message(self, message) -> None:
            self.rendered_messages.append(("user", message))

        def render(self, event) -> None:
            self.rendered_messages.append(("event", event))

        def render_segments(self, segments) -> None:
            self.rendered_segments.append(tuple(str(segment) for segment in segments))

    app = MockApplication()
    app.workspace = SimpleNamespace(root=Path.cwd().resolve())
    renderer = DummyRenderer()

    asyncio.run(run_mock_repl(app=app, renderer=renderer))

    assert len(renderer.rendered_messages) == 2
    assert renderer.rendered_messages[0][0] == "user"
    assert isinstance(renderer.rendered_messages[1][1], MarkdownEvent)
    assert len(renderer.rendered_segments) == 1
    assert len(renderer.rendered_segments[0]) == 3

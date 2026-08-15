from __future__ import annotations

from io import StringIO

from rich.console import Console
from rich.control import Control
from rich.panel import Panel

from cognieda.cli.renderer import Renderer
from cognieda.runtime.events import PlanProposed
from cognieda.runtime.messages import Message, MessageRole, MessageType
from cognieda.schemas import Objective, Plan, Task, TaskKind


def _renderer_output() -> tuple[Renderer, StringIO]:
    buffer = StringIO()
    return Renderer(Console(file=buffer, force_terminal=True, color_system="standard")), buffer


def test_render_user_message_uses_panel() -> None:
    class FakeConsole:
        def __init__(self) -> None:
            self.printed: list[object] = []

        def print(self, *objects: object, **_kwargs: object) -> None:
            self.printed.extend(objects)

    console = FakeConsole()
    renderer = Renderer(console=console)

    renderer.render(
        Message(
            role=MessageRole.USER,
            type=MessageType.TEXT,
            content="Need a summary",
        )
    )

    assert any(isinstance(item, Panel) for item in console.printed)


def test_render_assistant_message_uses_markdown_and_model_footer() -> None:
    renderer, buffer = _renderer_output()

    renderer.render(
        Message(
            role=MessageRole.ASSISTANT,
            type=MessageType.TEXT,
            content="# Result\n\nReady",
            model="gemini-2.5-flash",
        )
    )

    output = buffer.getvalue()
    assert "CogniEDA" in output
    assert "Result" in output
    assert "Ready" in output
    assert "◆ gemini-2.5-flash" in output


def test_render_segments_uses_shared_background_without_border() -> None:
    renderer, buffer = _renderer_output()

    renderer.render_segments(["first segment", "second segment"])

    output = buffer.getvalue()
    assert "first segment" in output
    assert "second segment" in output
    assert "╭" not in output
    assert "┌" not in output


def test_plan_event_handler_renders_transient_candidate() -> None:
    objective = Objective(text="Understand retention.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile retention cohorts.",
    )
    plan = Plan(
        objective=objective,
        tasks=(task,),
    )
    renderer, buffer = _renderer_output()

    renderer.handle_plan(PlanProposed(plan=plan))

    output = buffer.getvalue()
    assert "Proposed Plan" in output
    assert "Profile retention cohorts" in output


def test_read_input_uses_renderer_prompt_and_strips_whitespace() -> None:
    class FakeConsole:
        def __init__(self) -> None:
            self.prompt: str | None = None
            self.control_calls: list[object] = []

        def input(self, prompt: str) -> str:
            self.prompt = prompt
            return "  hello world  "

        def control(self, *controls: object) -> None:
            self.control_calls.extend(controls)

    mock_console = FakeConsole()
    renderer = Renderer(console=mock_console)

    text = renderer.read_input()

    assert text == "hello world"
    assert mock_console.prompt == ""
    assert mock_console.control_calls == []


def test_read_input_clears_prompt_line_for_interactive_terminal() -> None:
    class FakeConsole:
        def __init__(self) -> None:
            self.prompt: str | None = None
            self.control_calls: list[object] = []
            self.is_terminal = True
            self.is_dumb_terminal = False

        def input(self, prompt: str) -> str:
            self.prompt = prompt
            return "hello world"

        def control(self, *controls: object) -> None:
            self.control_calls.extend(controls)

    mock_console = FakeConsole()
    renderer = Renderer(console=mock_console)

    text = renderer.read_input()

    assert text == "hello world"
    assert mock_console.prompt == ""
    assert len(mock_console.control_calls) == 3
    assert all(isinstance(control, Control) for control in mock_console.control_calls)

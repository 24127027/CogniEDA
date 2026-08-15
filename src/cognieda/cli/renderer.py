from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from rich import box
from rich.console import Console
from rich.control import Control
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.segment import ControlType
from rich.text import Text

from cognieda.runtime.events import (
    HumanInputRequested,
    MessageProduced,
    PlanProposed,
)
from cognieda.runtime.messages import Message, MessageRole, MessageType
from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan import Plan

console = Console()


class Renderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or globals()["console"]

    def read_input(self) -> str:
        text = self.console.input("> ").strip()

        # Remove the terminal's echoed input line so only the styled user panel remains.
        is_terminal = getattr(self.console, "is_terminal", False) is True
        is_dumb_terminal = getattr(self.console, "is_dumb_terminal", True) is True
        if is_terminal and not is_dumb_terminal:
            self.console.control(
                Control.move(y=-1),
                Control.move_to_column(0),
                Control((ControlType.ERASE_IN_LINE, 2)),
            )

        return text

    def render_session_start(self, workspace_root: Path) -> None:
        self.console.print(f"[green]Workspace: {workspace_root}[/green]")
        self.console.print("[green]Session started.[/green]")

    def render_segments(self, segments: Iterable[str]) -> None:
        content = Text()
        segment_list = [str(segment) for segment in segments]

        for index, segment in enumerate(segment_list):
            content.append("● ", style="grey58")
            content.append(segment, style="grey70")

            if index < len(segment_list) - 1:
                content.append("\n\n")

        segment_area = Padding(
            content,
            pad=(1, 2),
            style="on #202020",
        )

        self.console.print(segment_area)

    def render(self, message: Message) -> None:
        match message.type, message.role:
            case MessageType.ERROR, _:
                self.console.print(f"[red][Error] {message.content}[/red]")

            case MessageType.TEXT, MessageRole.USER:
                self.console.print(
                    Panel(
                        str(message.content),
                        border_style="cyan",
                        box=box.ROUNDED,
                        padding=(0, 1),
                    )
                )

            case MessageType.TEXT, MessageRole.ASSISTANT:
                self.console.print("[bold cyan]CogniEDA[/bold cyan]")
                self.console.print(Markdown(str(message.content)))

                if message.model:
                    model_text = Text(
                        f"◆ {message.model}",
                        style="dim",
                        justify="right",
                    )
                    self.console.print(model_text)

            case _:
                self.console.print(str(message.content))

    def handle_message(self, event: MessageProduced) -> None:
        self.render(event.message)

    def handle_human_input(self, event: HumanInputRequested) -> None:
        self.render(event.message)

    def handle_plan(self, event: PlanProposed) -> None:
        self.render_plan(event.plan, event.tasks)

    def render_plan(
        self,
        plan: Plan,
        tasks: tuple[Task, ...],
    ) -> None:
        self.console.print("[bold cyan]Proposed Plan[/bold cyan]")

        for index, task in enumerate(tasks, start=1):
            self.console.print(f"{index}. {task}")

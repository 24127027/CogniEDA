from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import asyncio

from opentelemetry.trace import Status
from rich import box
from rich.console import Console
from rich.live import Live
from rich.control import Control
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.segment import ControlType
from rich.text import Text
from rich.status import Status
from rich.cells import cell_len

from cognieda.runtime.events import (
    AssistantThinkingFinished,
    AssistantThinkingStarted,
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
        prompt = "> "
        text = self.console.input(prompt).strip()

        if self.console.is_terminal and not self.console.is_dumb_terminal:
            self._erase_input(prompt, text)

        return text

    def _erase_input(self, prompt: str, text: str) -> None:
        width = self.console.width

        input_width = cell_len(prompt) + cell_len(text)
        rows = max(1, (input_width + width - 1) // width)

        controls = [Control.move(y=-rows)]

        for index in range(rows):
            controls.append(
                Control((ControlType.ERASE_IN_LINE, 2))
            )

            if index < rows - 1:
                controls.append(Control.move(y=1))

        controls.append(Control.move(y=1))
        controls.append(Control.move_to_column(0))

        self.console.control(*controls)

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

    async def render(self, message: Message) -> None:
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
                await self.render_assistant(message)
            case MessageType.TEXT, MessageRole.SYSTEM:
                self.console.print(
                    Panel(
                        Text(str(message.content), style="dim"),
                        border_style="grey50",
                        box=box.ROUNDED,
                        padding=(0, 1),
                        title="[dim]System[/dim]",
                        title_align="left",
                    )
                )
                
            case _:
                self.console.print(str(message.content))

    async def handle_message(self, event: MessageProduced) -> None:
        await self.render(event.message)

    async def handle_human_input(self, event: HumanInputRequested) -> None:
        await self.render(event.message)

    async def handle_plan(self, event: PlanProposed) -> None:
        await self.render_plan(event.plan, event.plan.tasks)

    async def render_plan(
        self,
        plan: Plan,
        tasks: tuple[Task, ...],
    ) -> None:
        self.console.print("[bold cyan]Proposed Plan[/bold cyan]")

        for index, task in enumerate(tasks, start=1):
            self.console.print(f"{index}. {task}")

    @staticmethod
    def _stream_chunks(
        text: str,
        *,
        chunk_size: int = 3,
    ) -> Iterable[str]:
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]

    async def render_assistant(self, message: Message) -> None:
        self.console.print("[bold cyan]CogniEDA[/bold cyan]")

        content = str(message.content)

        current = ""

        with Live(
            Markdown(""),
            console=self.console,
            refresh_per_second=30,
        ) as live:
            for chunk in self._stream_chunks(content):
                current += chunk
                live.update(Markdown(current))
                await asyncio.sleep(0.01 + len(chunk) * 0.003)
        if message.model:
            model_text = Text(
                f"◆ {message.model}",
                style="dim",
                justify="right",
            )
            self.console.print(model_text)

    def handle_thinking_started(
        self,
        event: AssistantThinkingStarted,
    ) -> None:
        self._thinking_status = Status(
            "CogniEDA is thinking",
            console=self.console,
            spinner="dots",
        )
        self._thinking_status.start()

    def handle_thinking_finished(
        self,
        event: AssistantThinkingFinished,
    ) -> None:
        if self._thinking_status is not None:
            self._thinking_status.stop()
            self._thinking_status = None
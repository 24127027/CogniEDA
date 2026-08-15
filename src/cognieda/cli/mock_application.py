from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from cognieda.runtime.messages import ErrorEvent, MarkdownEvent, StatusEvent, UIEvent

if TYPE_CHECKING:
    from cognieda.cli.renderer import Renderer


@dataclass(frozen=True)
class MockWorkspace:
    root: Path


class MockApplication:
    """Minimal runtime contract for UI-only rendering experiments."""

    def __init__(
        self,
        workspace_root: Path | None = None,
        *,
        model_name: str = "mock-ui-contract-v1",
    ) -> None:
        root = (workspace_root or Path.cwd()).expanduser().resolve()
        self.workspace = MockWorkspace(root=root)
        self.model_name = model_name
        self.received_messages: list[str] = []
        self.turn_count = 0

    async def submit_message(self, message: str) -> AsyncIterator[UIEvent]:
        """Yield deterministic UI presentation events without planner or model calls."""

        self.turn_count += 1
        text = message.strip()
        self.received_messages.append(text)

        lowered = text.casefold()
        if lowered == "/help":
            yield MarkdownEvent(
                content=(
                    "# Mock UI playground\n\n"
                    "Use these commands to stress renderer behavior:\n"
                    "- /showcase : render segments and assistant response in one turn\n"
                    "- /segments : render segment list preview\n"
                    "- /markdown : rich markdown sample\n"
                    "- /long : long paragraph wrapping sample\n"
                    "- /error your message : error surface\n"
                    "- any other input: echoed response\n"
                ),
                model=self.model_name,
            )
            return

        if lowered == "/markdown":
            yield StatusEvent("Planning...")
            yield MarkdownEvent(
                content=(
                    "# Render Sample\n\n"
                    "## Checklist\n"
                    "- objective captured\n"
                    "- assumptions listed\n"
                    "- next task proposed\n\n"
                    "## Code block\n"
                    "```python\n"
                    "def quality_gate(score: float) -> str:\n"
                    "    return 'pass' if score >= 0.8 else 'review'\n"
                    "```\n"
                ),
                model=self.model_name,
            )
            return

        if lowered == "/long":
            yield StatusEvent("Analyzing...")
            yield MarkdownEvent(
                content=(
                    "This is a deliberately long assistant response used to test line wrapping, "
                    "spacing consistency, and readability for dense content in narrow terminals. "
                    "It should remain readable and stable even when the viewport changes width."
                ),
                model=self.model_name,
            )
            return

        if lowered.startswith("/error"):
            details = text[6:].strip() or "Mock failure for renderer test"
            yield ErrorEvent(details)
            return

        yield StatusEvent("Planning...")
        yield MarkdownEvent(
            content=(
                f"Turn {self.turn_count}. You said: {text}\n\n"
                "Use /help for built-in UI render scenarios."
            ),
            model=self.model_name,
        )

    def showcase_preview(self, message: str) -> tuple[tuple[str, ...], MarkdownEvent] | None:
        """Return a full UI showcase: segment area + assistant response in one input."""

        lowered = message.strip().casefold()
        if lowered != "/showcase":
            return None

        segments = (
            "Showcase segment: request intake",
            "Showcase segment: normalized planning context",
            "Showcase segment: render-ready output",
        )
        response = MarkdownEvent(
            content=(
                "# Showcase Response\n\n"
                "This single command renders a full flow in one turn:\n"
                "- user bubble\n"
                "- segment strip\n"
                "- assistant markdown with model footer\n\n"
                "# Render Sample\n\n"
                "## Checklist\n"
                "- objective captured\n"
                "- assumptions listed\n"
                "- next task proposed\n\n"
                "## Code block\n"
                "```python\n"
                "def quality_gate(score: float) -> str:\n"
                "    return 'pass' if score >= 0.8 else 'review'\n"
                "```\n"
                "Use this to validate end-to-end visual rhythm."
            ),
            model=self.model_name,
        )
        return segments, response

    def segment_preview(self, message: str) -> tuple[str, ...] | None:
        """Return prebuilt segment lists for render_segments playground testing."""

        text = message.strip()
        if not text:
            return None

        lowered = text.casefold()
        if lowered == "/segments":
            return (
                "Segment preview: intake summary",
                "Segment preview: planning constraints",
                "Segment preview: next actions",
            )

        if lowered.startswith("/segments "):
            payload = text.split(" ", 1)[1].strip()
            if not payload:
                return None
            return tuple(part.strip() for part in payload.split("|") if part.strip())

        return None


async def run_mock_repl(
    workspace_root: Path | None = None,
    *,
    app: MockApplication | None = None,
    renderer: Renderer | None = None,
) -> None:
    """Start a planner-free REPL for experimenting with UI rendering behaviors."""

    from .renderer import Renderer

    resolved_app = app or MockApplication(workspace_root=workspace_root)
    resolved_renderer = renderer or Renderer()

    resolved_renderer.render_session_start(resolved_app.workspace.root)

    while True:
        text = resolved_renderer.read_input()

        if text in {"exit", "quit"}:
            break

        if not text:
            continue

        resolved_renderer.render_user_message(text)

        showcase = resolved_app.showcase_preview(text)
        if showcase is not None:
            segments, response = showcase
            resolved_renderer.render_segments(segments)
            resolved_renderer.render(response)
            continue

        segments = resolved_app.segment_preview(text)
        if segments is not None:
            resolved_renderer.render_segments(segments)
            continue

        async for event in resolved_app.submit_message(text):
            resolved_renderer.render(event)


def main() -> None:
    asyncio.run(run_mock_repl())


if __name__ == "__main__":
    main()

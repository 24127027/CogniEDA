from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cognieda.runtime.messages import Message, MessageRole, MessageType


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
        self.workspace = MockWorkspace(
            root=(workspace_root or Path.cwd()).expanduser().resolve()
        )
        self.model_name = model_name
        self.turn_count = 0
        self.received_messages: list[str] = []

    async def submit_message(self, message: str) -> Message:
        self.turn_count += 1

        text = message.strip()
        self.received_messages.append(text)
        lowered = text.casefold()

        if lowered == "/help":
            return Message(
                role=MessageRole.ASSISTANT,
                type=MessageType.TEXT,
                model=self.model_name,
                content=(
                    "# Mock UI playground\n\n"
                    "Available commands:\n"
                    "- /markdown\n"
                    "- /long\n"
                    "- /error your message\n"
                ),
            )

        if lowered == "/markdown":
            return Message(
                role=MessageRole.ASSISTANT,
                type=MessageType.TEXT,
                model=self.model_name,
                content=(
                    "# Render Sample\n\n"
                    "## Checklist\n"
                    "- objective captured\n"
                    "- assumptions listed\n"
                    "- next task proposed\n\n"
                    "```python\n"
                    "def quality_gate(score: float) -> str:\n"
                    "    return 'pass' if score >= 0.8 else 'review'\n"
                    "```\n"
                ),
            )

        if lowered == "/long":
            return Message(
                role=MessageRole.ASSISTANT,
                type=MessageType.TEXT,
                model=self.model_name,
                content=(
                    "This is a deliberately long assistant response used to "
                    "test wrapping and spacing inside the renderer."
                ),
            )

        if lowered.startswith("/error"):
            return Message(
                role=MessageRole.ASSISTANT,
                type=MessageType.ERROR,
                model=self.model_name,
                content=text[6:].strip() or "Mock failure for renderer test",
            )

        return Message(
            role=MessageRole.ASSISTANT,
            type=MessageType.TEXT,
            model=self.model_name,
            content=(
                f"Turn {self.turn_count}. You said: {text}\n\n"
                "Use /help for built-in scenarios."
            ),
        )
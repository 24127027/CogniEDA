from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from cognieda.cli.renderer import Renderer
    from cognieda.runtime.messages import Message, MessageRole, MessageType
else:
    from .renderer import Renderer
    from ..runtime.messages import Message, MessageRole, MessageType

if TYPE_CHECKING:
    from cognieda.runtime import Application


async def repl(app: Application, renderer: Renderer) -> None:
    renderer.render_session_start(app.workspace.root)

    while True:
        text = renderer.read_input()

        if text in {"exit", "quit"}:
            break

        if not text:
            continue

        renderer.render(
            Message(
                type=MessageType.TEXT,
                role=MessageRole.USER,
                content=text,
            )
        )
        response = await app.submit_message(text)
        renderer.render(response)

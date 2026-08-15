from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from cognieda.runtime.events import HumanInputRequested, MessageProduced, PlanProposed

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from cognieda.cli.renderer import Renderer
    from cognieda.runtime.messages import Message, MessageRole, MessageType
else:
    from ..runtime.messages import Message, MessageRole, MessageType
    from .renderer import Renderer

if TYPE_CHECKING:
    from cognieda.runtime import Application


async def repl(app: Application, renderer: Renderer) -> None:
    app.event_bus.subscribe(
        MessageProduced,
        renderer.handle_message,
    )
    app.event_bus.subscribe(
        HumanInputRequested,
        renderer.handle_human_input,
    )
    app.event_bus.subscribe(
        PlanProposed,
        renderer.handle_plan,
    )

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

        await app.submit_message(text)

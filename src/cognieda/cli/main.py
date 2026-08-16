from __future__ import annotations

from typing import TYPE_CHECKING

from cognieda.cli.renderer import Renderer
from cognieda.runtime.events import HumanInputRequested, MessageProduced, PlanProposed
from cognieda.runtime.messages import Message, MessageRole, MessageType

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

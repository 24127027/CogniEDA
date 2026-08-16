from __future__ import annotations

from typing import TYPE_CHECKING

from cognieda.runtime.events import MessageProduced, PlanProposed
from .prompt import Prompt
from .renderer import Renderer

if TYPE_CHECKING:
    from cognieda.runtime import Application


async def repl(app: Application, renderer: Renderer) -> None:
    app.event_bus.subscribe(
        MessageProduced,
        renderer.handle_message,
    )
    app.event_bus.subscribe(
        PlanProposed,
        renderer.handle_plan,
    )

    renderer.render_session_start(app.workspace.root)

    prompt = Prompt(app)

    while True:
        try:
            text = (await prompt.read()).strip()
        except (EOFError, KeyboardInterrupt):
            break

        if text in {"exit", "quit"}:
            break

        if not text:
            continue

        await app.submit_message(text)
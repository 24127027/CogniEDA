from __future__ import annotations

from typing import TYPE_CHECKING

from cognieda.runtime.events import (
    AssistantThinkingFinished, 
    AssistantThinkingStarted, 
    MessageProduced, 
    PlanProposed
)
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
    app.event_bus.subscribe(
        AssistantThinkingStarted,
        renderer.handle_thinking_started,
    )
    app.event_bus.subscribe(
        AssistantThinkingFinished,
        renderer.handle_thinking_finished,
    )

    prompt = Prompt(app)

    if app.workspace.project_config.try_resolve_model() is None:
        await app.submit_message("/provider.config")

    renderer.render_session_start(app.workspace.root)

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
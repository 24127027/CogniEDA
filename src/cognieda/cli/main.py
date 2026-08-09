from __future__ import annotations

from typing import TYPE_CHECKING

from .renderer import Renderer

if TYPE_CHECKING:
    from cognieda.runtime import Application


async def repl(app: Application, renderer: Renderer) -> None:
    await app.start_session()

    while True:
        text = input("> ").strip()

        if text in {"exit", "quit"}:
            break

        if not text:
            continue

        response = await app.submit_message(text)
        renderer.render(response)

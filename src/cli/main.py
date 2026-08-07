from ..runtime import Application
from .renderer import Renderer

async def repl(app: Application, renderer: Renderer):
    await app.start_session()

    while True:
        text = input("> ").strip()

        if text in {"exit", "quit"}:
            break

        if not text:
            continue

        response = await app.submit_message(text)
        renderer.render(response)
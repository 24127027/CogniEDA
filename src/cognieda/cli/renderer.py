from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cognieda.runtime.messages import Message


class Renderer:
    def render(self, message: Message) -> None:
        from cognieda.runtime.messages import MessageType

        match message.type:
            case MessageType.TEXT:
                print(f"CogniEDA: {message.content}")

            case MessageType.ERROR:
                print(f"Error: {message.content}")

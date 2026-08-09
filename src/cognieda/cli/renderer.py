from cognieda.runtime.messages import Message, MessageType


class Renderer:
    def render(self, message: Message) -> None:
        match message.type:
            case MessageType.TEXT:
                print(f"CogniEDA: {message.content}")

            case MessageType.ERROR:
                print(f"Error: {message.content}")

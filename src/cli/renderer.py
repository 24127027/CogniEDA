from ..runtime import Message, MessageType

class Renderer:
    def render(self, message: Message):
        # Implement the logic to render the message in the CLI
        print(message.content)
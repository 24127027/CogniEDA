from typing import TYPE_CHECKING, Any

from .messages import Message, MessageType

if TYPE_CHECKING:
    from .application import Application
    from .bootstrap import bootstrap_application
    from .conversation.conversation import ConversationHistory, ConversationSegment, ConversationTurn

__all__ = [
    "Application",
    "ConversationHistory",
    "ConversationSegment",
    "ConversationTurn",
    "Message",
    "MessageType",
    "bootstrap_application",
]


def __getattr__(name: str) -> Any:
    if name == "Application":
        from .application import Application

        return Application
    if name == "bootstrap_application":
        from .bootstrap import bootstrap_application

        return bootstrap_application
    if name in {"ConversationHistory", "ConversationSegment", "ConversationTurn"}:
        import cognieda.runtime.conversation.conversation as conversation_module

        return getattr(conversation_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

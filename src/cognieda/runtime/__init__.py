from typing import TYPE_CHECKING, Any

from .messages import Message, MessageType

if TYPE_CHECKING:
    from .application import Application
    from .bootstrap import bootstrap_application

__all__ = ["Application", "Message", "MessageType", "bootstrap_application"]


def __getattr__(name: str) -> Any:
    if name == "Application":
        from .application import Application

        return Application
    if name == "bootstrap_application":
        from .bootstrap import bootstrap_application

        return bootstrap_application
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

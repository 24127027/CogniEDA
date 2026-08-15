from dataclasses import dataclass
from enum import Enum
from typing import Any


class MessageRole(str, Enum):  # noqa: UP042 - preserve the existing runtime contract
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class MessageType(str, Enum):  # noqa: UP042 - preserve the existing runtime contract
    TEXT = "text"
    ERROR = "error"


@dataclass(frozen=True)
class UIEvent:
    """Presentation-only data that can be rendered by the UI layer."""


@dataclass(frozen=True)
class MarkdownEvent(UIEvent):
    content: str
    model: str | None = None


@dataclass(frozen=True)
class StatusEvent(UIEvent):
    content: str


@dataclass(frozen=True)
class ErrorEvent(UIEvent):
    content: str


@dataclass
class Message:
    role: MessageRole
    type: MessageType
    content: Any
    model: str | None = None


@dataclass
class MockMessage:
    role: MessageRole
    type: MessageType
    content: Any
    model: str | None = None

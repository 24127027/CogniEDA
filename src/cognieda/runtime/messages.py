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
    THINNKING = "thinking"
    INPUT_REQUEST = "input_request"

@dataclass
class Message:
    role: MessageRole
    type: MessageType
    content: Any
    model: str | None = None

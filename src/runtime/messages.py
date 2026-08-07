from dataclasses import dataclass
from enum import Enum
from typing import Any

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class MessageType(str, Enum):
    TEXT = "text"
    ERROR = "error"

@dataclass
class Message:
    role: MessageRole
    type: MessageType
    content: Any
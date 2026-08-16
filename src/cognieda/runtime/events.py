from dataclasses import dataclass

from pydantic_ai.messages import ModelMessage

from cognieda.runtime.messages import Message
from cognieda.schemas.plan import Plan


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    pass


@dataclass(frozen=True, slots=True)
class MessageProduced(RuntimeEvent):
    message: Message


@dataclass(frozen=True, slots=True)
class PlanProposed(RuntimeEvent):
    plan: Plan
    

@dataclass(frozen=True, slots=True)
class ApplicationError(RuntimeEvent):
    error: Exception

# TODO: Temporary event types for conversation projector. 
# These should be replaced with more general events in the future.
@dataclass(frozen=True, slots=True)
class ModelMessageProduced(RuntimeEvent):
    message: ModelMessage
    visible: bool = True

@dataclass(frozen=True, slots=True) 
class SegmentCompleted(RuntimeEvent):
    pass

@dataclass(frozen=True, slots=True)
class TurnCompleted(RuntimeEvent):
    pass

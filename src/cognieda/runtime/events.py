from dataclasses import dataclass

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
class HumanInputRequested(RuntimeEvent):
    message: Message


@dataclass(frozen=True, slots=True)
class ApplicationError(RuntimeEvent):
    error: Exception

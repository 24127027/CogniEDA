from dataclasses import dataclass

from cognieda.agents.planner.types import Plan, Task
from cognieda.runtime.messages import Message


@dataclass(frozen=True, slots=True)
class RuntimeEvent:
    pass


@dataclass(frozen=True, slots=True)
class MessageProduced(RuntimeEvent):
    message: Message


@dataclass(frozen=True, slots=True)
class PlanProposed(RuntimeEvent):
    plan: Plan
    tasks: tuple[Task, ...]


@dataclass(frozen=True, slots=True)
class HumanInputRequested(RuntimeEvent):
    message: Message


@dataclass(frozen=True, slots=True)
class ApplicationError(RuntimeEvent):
    error: Exception
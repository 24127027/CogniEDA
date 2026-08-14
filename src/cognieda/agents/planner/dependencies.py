from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.execution import ExecutorContext
from cognieda.schemas.artifacts import DataProfile, Task
from cognieda.schemas.plan import Plan


@dataclass(frozen=True)
class PlannerDeps:
    """Model-hidden runtime authority and services available through RunContext."""

    dispatcher: ExecutorDispatcherPort
    executor_tools_enabled: bool = False
    approved_plan: Plan | None = None
    approved_tasks: tuple[Task, ...] = ()
    eligible_task_ids: frozenset[UUID] = frozenset()
    execution_context: ExecutorContext = field(default_factory=ExecutorContext)
    data_profile: DataProfile | None = None


__all__ = ("PlannerDeps",)

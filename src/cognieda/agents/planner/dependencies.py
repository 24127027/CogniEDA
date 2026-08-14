from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan import Plan


@dataclass(frozen=True)
class PlannerDeps:
    """Model-hidden runtime authority and services available through RunContext."""

    dispatcher: ExecutorDispatcherPort
    executor_tools_enabled: bool = False
    approved_plan: Plan | None = None
    approved_tasks: tuple[Task, ...] = ()
    eligible_task_ids: frozenset[UUID] = frozenset()


__all__ = ("PlannerDeps",)

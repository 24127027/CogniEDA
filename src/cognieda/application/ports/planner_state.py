from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cognieda.schemas.artifacts import Assumption, Objective, Task
from cognieda.schemas.enums import TaskStatus


class PlannerStateMutationPort(Protocol):
    """Application-owned mutation and lifecycle seam used by Planner nodes."""

    def create_objective(self, objective: Objective) -> Objective: ...

    def create_assumption(self, assumption: Assumption) -> Assumption: ...

    def create_task(self, task: Task) -> Task: ...

    def transition_task_status(self, task_id: UUID, status: TaskStatus) -> Task | None: ...

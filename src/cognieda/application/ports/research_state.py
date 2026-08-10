from __future__ import annotations

from typing import Protocol
from uuid import UUID

from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    Task,
)
from cognieda.schemas.enums import TaskStatus


class PlannerResearchStatePort(Protocol):
    """Authoritative research-object seam used to build and advance Planner context."""

    def get_objective(self, objective_id: UUID) -> Objective | None: ...

    def get_assumption(self, assumption_id: UUID) -> Assumption | None: ...

    def get_task(self, task_id: UUID) -> Task | None: ...

    def get_data_profile(self, data_profile_id: UUID) -> DataProfile | None: ...

    def get_evidence(self, evidence_id: UUID) -> Evidence | None: ...

    def create_objective(self, objective: Objective) -> Objective: ...

    def create_assumption(self, assumption: Assumption) -> Assumption: ...

    def create_task(self, task: Task) -> Task: ...

    def update_task_status(self, task_id: UUID, status: TaskStatus) -> Task | None: ...

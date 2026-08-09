from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from cognieda.infrastructure.persistence.repositories import (
    AssumptionRepository,
    DataProfileRepository,
    EvidenceRepository,
    ObjectiveRepository,
    TaskRepository,
    TaskUpdate,
)
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    Task,
)
from cognieda.schemas.enums import TaskStatus


class SqlitePlannerResearchState:
    """SQLite-backed authoritative object seam for the bounded Planner runtime."""

    def __init__(self, session: Session) -> None:
        self._objectives = ObjectiveRepository(session)
        self._assumptions = AssumptionRepository(session)
        self._tasks = TaskRepository(session)
        self._profiles = DataProfileRepository(session)
        self._evidence = EvidenceRepository(session)

    def get_objective(self, objective_id: UUID) -> Objective | None:
        return self._objectives.get_by_id(objective_id)

    def get_assumption(self, assumption_id: UUID) -> Assumption | None:
        return self._assumptions.get_by_id(assumption_id)

    def get_task(self, task_id: UUID) -> Task | None:
        return self._tasks.get_by_id(task_id)

    def get_data_profile(self, data_profile_id: UUID) -> DataProfile | None:
        return self._profiles.get_by_id(data_profile_id)

    def get_evidence(self, evidence_id: UUID) -> Evidence | None:
        return self._evidence.get_by_id(evidence_id)

    def create_objective(self, objective: Objective) -> Objective:
        return self._objectives.create(objective)

    def create_assumption(self, assumption: Assumption) -> Assumption:
        return self._assumptions.create(assumption)

    def create_task(self, task: Task) -> Task:
        return self._tasks.create(task)

    def update_task_status(self, task_id: UUID, status: TaskStatus) -> Task | None:
        return self._tasks.update(task_id, TaskUpdate(status=status))

"""Side-effect-free validation of exact canonical Plan candidates."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from uuid import UUID

from pydantic import ValidationError
from sqlmodel import Session

from cognieda.infrastructure.persistence.repositories import (
    AssumptionRepository,
    ObjectiveRepository,
    TaskRepository,
)
from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan import Plan


class PlanValidationErrorCode(StrEnum):
    """Finite fail-closed candidate rejection categories."""

    INVALID_IDENTITY = "invalid_identity"
    OBJECTIVE_NOT_FOUND = "objective_not_found"
    OBJECTIVE_CONTENT_MISMATCH = "objective_content_mismatch"
    ASSUMPTION_NOT_FOUND = "assumption_not_found"
    ASSUMPTION_CONTENT_MISMATCH = "assumption_content_mismatch"
    TASK_NOT_FOUND = "task_not_found"
    TASK_OBJECTIVE_MISMATCH = "task_objective_mismatch"
    INVALID_CANDIDATE = "invalid_candidate"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"


class PlanValidationError(ValueError):
    def __init__(self, code: PlanValidationErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


class PlanValidator:
    """Validate exact Plan content against authoritative persisted FCOs."""

    def __init__(self, session: Session) -> None:
        self._objectives = ObjectiveRepository(session)
        self._assumptions = AssumptionRepository(session)
        self._tasks = TaskRepository(session)

    def validate(
        self,
        candidate: Plan,
        *,
        tasks: Iterable[Task] | None = None,
    ) -> Plan:
        """Return canonical content without persistence or runtime inspection."""

        if not isinstance(candidate.plan_id, UUID):
            raise PlanValidationError(
                PlanValidationErrorCode.INVALID_IDENTITY,
                "Plan candidate requires an exact UUID identity.",
            )
        objective = self._objectives.get_by_id(candidate.objective.objective_id)
        if objective is None:
            raise PlanValidationError(
                PlanValidationErrorCode.OBJECTIVE_NOT_FOUND,
                "Plan candidate requires a persisted Objective.",
            )
        if objective != candidate.objective:
            raise PlanValidationError(
                PlanValidationErrorCode.OBJECTIVE_CONTENT_MISMATCH,
                "Plan Objective differs from the authoritative persisted Objective.",
            )

        assumptions = []
        for assumption in candidate.assumptions:
            persisted = self._assumptions.get_by_id(assumption.assumption_id)
            if persisted is None:
                raise PlanValidationError(
                    PlanValidationErrorCode.ASSUMPTION_NOT_FOUND,
                    "Plan candidate references a missing persisted Assumption.",
                )
            if persisted != assumption:
                raise PlanValidationError(
                    PlanValidationErrorCode.ASSUMPTION_CONTENT_MISMATCH,
                    "Plan Assumption differs from the authoritative persisted Assumption.",
                )
            assumptions.append(persisted)

        supplied_tasks = None if tasks is None else tuple(tasks)
        if supplied_tasks is not None:
            try:
                candidate.validate_tasks(supplied_tasks)
            except ValueError as exc:
                raise PlanValidationError(
                    PlanValidationErrorCode.INVALID_CANDIDATE,
                    f"Plan candidate Task bundle is invalid: {exc}",
                ) from exc

        persisted_tasks: list[Task] = []
        for task_id in candidate.task_ids:
            task = self._tasks.get_by_id(task_id)
            if task is None:
                raise PlanValidationError(
                    PlanValidationErrorCode.TASK_NOT_FOUND,
                    "Plan candidate references a missing persisted Task.",
                )
            if task.objective_id != candidate.objective.objective_id:
                raise PlanValidationError(
                    PlanValidationErrorCode.TASK_OBJECTIVE_MISMATCH,
                    "Every persisted Task must belong to the Plan Objective.",
                )
            persisted_tasks.append(task)

        try:
            canonical = Plan.model_validate(
                {
                    "plan_id": candidate.plan_id,
                    "objective": objective,
                    "assumptions": assumptions,
                    "task_ids": candidate.task_ids,
                    "dependencies": [
                        {
                            "prerequisite_task_id": dependency.prerequisite_task_id,
                            "dependent_task_ids": dependency.dependent_task_ids,
                        }
                        for dependency in candidate.dependencies
                    ],
                }
            )
            canonical.validate_tasks(persisted_tasks)
        except (TypeError, ValueError, ValidationError) as exc:
            raise PlanValidationError(
                PlanValidationErrorCode.INVALID_CANDIDATE,
                f"Plan candidate is structurally invalid: {exc}",
            ) from exc

        candidate_content = candidate.model_dump(mode="json", exclude={"fingerprint"})
        canonical_content = canonical.model_dump(mode="json", exclude={"fingerprint"})
        if candidate_content != canonical_content:
            raise PlanValidationError(
                PlanValidationErrorCode.INVALID_CANDIDATE,
                "Plan candidate representation is not structurally canonical.",
            )
        if candidate.fingerprint != canonical.fingerprint:
            raise PlanValidationError(
                PlanValidationErrorCode.FINGERPRINT_MISMATCH,
                "Plan candidate fingerprint does not match exact canonical content.",
            )
        return canonical


__all__ = (
    "PlanValidationError",
    "PlanValidationErrorCode",
    "PlanValidator",
)

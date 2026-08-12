"""Side-effect-free validation of exact canonical PlanRevision candidates."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import ValidationError
from sqlmodel import Session

from cognieda.infrastructure.persistence.repositories import (
    ObjectiveRepository,
    TaskRepository,
)
from cognieda.schemas.plan_revision import (
    PLAN_REVISION_CONTRACT_VERSION,
    PlanRevision,
)


class PlanRevisionValidationErrorCode(StrEnum):
    """Finite fail-closed candidate rejection categories."""

    INVALID_IDENTITY = "invalid_identity"
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    OBJECTIVE_NOT_FOUND = "objective_not_found"
    TASK_NOT_FOUND = "task_not_found"
    TASK_OBJECTIVE_MISMATCH = "task_objective_mismatch"
    INVALID_CANDIDATE = "invalid_candidate"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"


class PlanRevisionValidationError(ValueError):
    def __init__(self, code: PlanRevisionValidationErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


class PlanRevisionValidator:
    """Validate a candidate against authoritative references without persistence."""

    def __init__(self, session: Session) -> None:
        self._objectives = ObjectiveRepository(session)
        self._tasks = TaskRepository(session)

    def validate(self, candidate: PlanRevision) -> PlanRevision:
        """Return the exact canonical candidate without admitting or mutating state."""

        if not isinstance(candidate.plan_revision_id, UUID) or not isinstance(
            candidate.objective_id, UUID
        ):
            raise PlanRevisionValidationError(
                PlanRevisionValidationErrorCode.INVALID_IDENTITY,
                "PlanRevision candidate requires exact UUID identities.",
            )
        if candidate.contract_version != PLAN_REVISION_CONTRACT_VERSION:
            raise PlanRevisionValidationError(
                PlanRevisionValidationErrorCode.UNSUPPORTED_CONTRACT_VERSION,
                "PlanRevision candidate uses an unsupported contract version.",
            )
        if self._objectives.get_by_id(candidate.objective_id) is None:
            raise PlanRevisionValidationError(
                PlanRevisionValidationErrorCode.OBJECTIVE_NOT_FOUND,
                "PlanRevision candidate requires an authoritative Objective.",
            )

        authoritative_tasks = []
        for binding in candidate.task_bindings:
            task = self._tasks.get_by_id(binding.task_id)
            if task is None:
                raise PlanRevisionValidationError(
                    PlanRevisionValidationErrorCode.TASK_NOT_FOUND,
                    "PlanRevision candidate references a missing authoritative Task.",
                )
            if task.objective_id != candidate.objective_id:
                raise PlanRevisionValidationError(
                    PlanRevisionValidationErrorCode.TASK_OBJECTIVE_MISMATCH,
                    "Every authoritative Task must belong to the candidate Objective.",
                )
            authoritative_tasks.append(task)

        try:
            canonical = PlanRevision.model_validate(
                {
                    "plan_revision_id": candidate.plan_revision_id,
                    "objective_id": candidate.objective_id,
                    "task_bindings": [
                        {
                            "task_id": binding.task_id,
                            "required_capability": binding.required_capability,
                            "order_rank": binding.order_rank,
                            "priority": binding.priority,
                        }
                        for binding in candidate.task_bindings
                    ],
                    "dependencies": [
                        {
                            "prerequisite_task_id": dependency.prerequisite_task_id,
                            "dependent_task_id": dependency.dependent_task_id,
                        }
                        for dependency in candidate.dependencies
                    ],
                    "contract_version": candidate.contract_version,
                },
                context={"authoritative_tasks": tuple(authoritative_tasks)},
            )
        except (TypeError, ValueError, ValidationError) as exc:
            raise PlanRevisionValidationError(
                PlanRevisionValidationErrorCode.INVALID_CANDIDATE,
                f"PlanRevision candidate is structurally invalid: {exc}",
            ) from exc

        candidate_content = candidate.model_dump(mode="json", exclude={"fingerprint"})
        canonical_content = canonical.model_dump(mode="json", exclude={"fingerprint"})
        if candidate_content != canonical_content:
            raise PlanRevisionValidationError(
                PlanRevisionValidationErrorCode.INVALID_CANDIDATE,
                "PlanRevision candidate representation is not structurally canonical.",
            )
        if candidate.fingerprint != canonical.fingerprint:
            raise PlanRevisionValidationError(
                PlanRevisionValidationErrorCode.FINGERPRINT_MISMATCH,
                "PlanRevision candidate fingerprint does not match exact canonical content.",
            )
        return canonical


__all__ = (
    "PlanRevisionValidationError",
    "PlanRevisionValidationErrorCode",
    "PlanRevisionValidator",
)

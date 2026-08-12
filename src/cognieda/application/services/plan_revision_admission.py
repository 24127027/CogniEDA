"""Application-owned admission of exact immutable PlanRevision proposals."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, SkipValidation, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from cognieda.infrastructure.persistence.repositories import (
    ObjectiveRepository,
    PlanRevisionRepository,
    TaskRepository,
)
from cognieda.schemas.plan_revision import (
    PLAN_REVISION_CONTRACT_VERSION,
    PlanRevision,
)


class PlanRevisionAdmissionErrorCode(StrEnum):
    """Finite fail-closed proposal rejection categories."""

    INVALID_IDENTITY = "invalid_identity"
    UNSUPPORTED_CONTRACT_VERSION = "unsupported_contract_version"
    OBJECTIVE_NOT_FOUND = "objective_not_found"
    TASK_NOT_FOUND = "task_not_found"
    TASK_OBJECTIVE_MISMATCH = "task_objective_mismatch"
    INVALID_PROPOSAL = "invalid_proposal"
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"
    IDENTITY_COLLISION = "identity_collision"


class PlanRevisionAdmissionError(ValueError):
    def __init__(self, code: PlanRevisionAdmissionErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


class PlanRevisionAdmissionResult(BaseModel):
    """Durable admitted proposal plus exact-replay disposition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_revision: SkipValidation[PlanRevision]
    created: bool


class PlanRevisionAdmissionService:
    """Validate authoritative references and atomically admit one proposal."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._objectives = ObjectiveRepository(session)
        self._tasks = TaskRepository(session)
        self._revisions = PlanRevisionRepository(session)

    def _canonical_candidate(self, candidate: PlanRevision) -> PlanRevision:
        if not isinstance(candidate.plan_revision_id, UUID) or not isinstance(
            candidate.objective_id, UUID
        ):
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.INVALID_IDENTITY,
                "PlanRevision proposal requires exact UUID identities.",
            )
        if candidate.contract_version != PLAN_REVISION_CONTRACT_VERSION:
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.UNSUPPORTED_CONTRACT_VERSION,
                "PlanRevision proposal uses an unsupported contract version.",
            )
        if self._objectives.get_by_id(candidate.objective_id) is None:
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.OBJECTIVE_NOT_FOUND,
                "PlanRevision proposal requires an authoritative Objective.",
            )

        authoritative_tasks = []
        for binding in candidate.task_bindings:
            task = self._tasks.get_by_id(binding.task_id)
            if task is None:
                raise PlanRevisionAdmissionError(
                    PlanRevisionAdmissionErrorCode.TASK_NOT_FOUND,
                    "PlanRevision proposal references a missing authoritative Task.",
                )
            if task.objective_id != candidate.objective_id:
                raise PlanRevisionAdmissionError(
                    PlanRevisionAdmissionErrorCode.TASK_OBJECTIVE_MISMATCH,
                    "Every authoritative Task must belong to the proposal Objective.",
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
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.INVALID_PROPOSAL,
                f"PlanRevision proposal is structurally invalid: {exc}",
            ) from exc

        candidate_content = candidate.model_dump(mode="json", exclude={"fingerprint"})
        canonical_content = canonical.model_dump(mode="json", exclude={"fingerprint"})
        if candidate_content != canonical_content:
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.INVALID_PROPOSAL,
                "PlanRevision proposal representation is not structurally canonical.",
            )
        if candidate.fingerprint != canonical.fingerprint:
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.FINGERPRINT_MISMATCH,
                "PlanRevision proposal fingerprint does not match exact canonical content.",
            )
        return canonical

    def admit_proposal(self, candidate: PlanRevision) -> PlanRevisionAdmissionResult:
        """Admit a proposal without approving, activating, or executing it."""

        canonical = self._canonical_candidate(candidate)
        try:
            existing = self._revisions.get_by_id(canonical.plan_revision_id)
        except ValueError as exc:
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.FINGERPRINT_MISMATCH,
                str(exc),
            ) from exc
        if existing is not None:
            if existing == canonical and existing.fingerprint == canonical.fingerprint:
                return PlanRevisionAdmissionResult(
                    plan_revision=existing,
                    created=False,
                )
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.IDENTITY_COLLISION,
                "PlanRevision identity already exists with different canonical content.",
            )

        try:
            self._revisions.add(canonical)
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            try:
                concurrent = self._revisions.get_by_id(canonical.plan_revision_id)
            except ValueError as exc:
                raise PlanRevisionAdmissionError(
                    PlanRevisionAdmissionErrorCode.FINGERPRINT_MISMATCH,
                    str(exc),
                ) from exc
            if concurrent == canonical and concurrent is not None:
                return PlanRevisionAdmissionResult(
                    plan_revision=concurrent,
                    created=False,
                )
            raise PlanRevisionAdmissionError(
                PlanRevisionAdmissionErrorCode.IDENTITY_COLLISION,
                "Concurrent PlanRevision admission produced an identity conflict.",
            ) from None
        except Exception:
            self._session.rollback()
            raise

        admitted = self._revisions.get_by_id(canonical.plan_revision_id)
        if admitted is None:
            raise RuntimeError("Committed PlanRevision proposal could not be reloaded.")
        return PlanRevisionAdmissionResult(plan_revision=admitted, created=True)


__all__ = (
    "PlanRevisionAdmissionError",
    "PlanRevisionAdmissionErrorCode",
    "PlanRevisionAdmissionResult",
    "PlanRevisionAdmissionService",
)

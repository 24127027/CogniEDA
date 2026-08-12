"""Transient Planner proposal contracts for exact Human approval."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import Field, NonNegativeInt, computed_field, field_validator, model_validator

from cognieda.execution.capabilities import Capability
from cognieda.schemas.artifacts import Objective
from cognieda.schemas.common import ImmutableCogniEDABaseModel, NonEmptyStr
from cognieda.schemas.enums import PlanPriority, TaskKind


class TaskDraft(ImmutableCogniEDABaseModel):
    """Non-authoritative proposed semantic Task plus revision coordination."""

    task_draft_id: UUID = Field(default_factory=uuid4)
    kind: TaskKind
    instruction: NonEmptyStr
    required_capability: Capability
    order_rank: NonNegativeInt
    priority: PlanPriority = PlanPriority.NORMAL


class PlanDraftDependency(ImmutableCogniEDABaseModel):
    """Proposed prerequisite edge referring only to exact draft Task identities."""

    prerequisite_task_draft_id: UUID
    dependent_task_draft_id: UUID

    @model_validator(mode="after")
    def _reject_self_dependency(self) -> PlanDraftDependency:
        if self.prerequisite_task_draft_id == self.dependent_task_draft_id:
            raise ValueError("PlanDraftDependency rejects a self dependency.")
        return self


class PlanDraft(ImmutableCogniEDABaseModel):
    """Exact non-authoritative Objective and Task proposal presented for approval."""

    plan_draft_id: UUID = Field(default_factory=uuid4)
    objective: Objective
    task_drafts: tuple[TaskDraft, ...] = Field(min_length=1)
    dependencies: tuple[PlanDraftDependency, ...] = ()

    @model_validator(mode="after")
    def _require_unambiguous_draft_references(self) -> PlanDraft:
        task_ids = [task.task_draft_id for task in self.task_drafts]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("PlanDraft rejects duplicate TaskDraft identities.")

        member_ids = set(task_ids)
        edges = [
            (
                dependency.prerequisite_task_draft_id,
                dependency.dependent_task_draft_id,
            )
            for dependency in self.dependencies
        ]
        if len(edges) != len(set(edges)):
            raise ValueError("PlanDraft rejects duplicate dependency edges.")
        if any(
            prerequisite_id not in member_ids or dependent_id not in member_ids
            for prerequisite_id, dependent_id in edges
        ):
            raise ValueError("PlanDraft dependencies must refer to member TaskDrafts.")
        return self

    @computed_field(return_type=str)  # type: ignore[prop-decorator]
    @property
    def fingerprint(self) -> str:
        """Bind approval to the exact structural proposal without semantic inference."""

        payload = {
            "plan_draft_id": str(self.plan_draft_id),
            "objective": self.objective.model_dump(mode="json"),
            "task_drafts": [task.model_dump(mode="json") for task in self.task_drafts],
            "dependencies": [
                dependency.model_dump(mode="json") for dependency in self.dependencies
            ],
        }
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(serialized).hexdigest()}"


class PlanDraftDecision(StrEnum):
    """Minimum explicit Human decision for one exact transient draft."""

    APPROVE = "approve"
    REJECT = "reject"


class PlanDraftApproval(ImmutableCogniEDABaseModel):
    """Human decision bound to one exact PlanDraft snapshot."""

    plan_draft_id: UUID
    plan_draft_fingerprint: str
    decision: PlanDraftDecision

    @field_validator("plan_draft_fingerprint")
    @classmethod
    def _require_sha256_fingerprint(cls, value: str) -> str:
        if len(value) != 71 or not value.startswith("sha256:"):
            raise ValueError("PlanDraft approval requires an exact sha256 fingerprint.")
        try:
            int(value.removeprefix("sha256:"), 16)
        except ValueError as exc:
            raise ValueError("PlanDraft approval requires an exact sha256 fingerprint.") from exc
        return value


__all__ = (
    "PlanDraft",
    "PlanDraftApproval",
    "PlanDraftDecision",
    "PlanDraftDependency",
    "TaskDraft",
)

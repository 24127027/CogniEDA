from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import Task

from .capabilities import Capability


class ExecutorContext(BaseModel):
    """Small shared context that is safe for every registered executor."""

    model_config = ConfigDict(extra="forbid")

    dataset_path: str | None = None
    data_profile_id: UUID | None = None

class ExecutorRequest(BaseModel):
    """Typed capability request sent through the executor dispatcher."""

    model_config = ConfigDict(extra="forbid")

    capability: Capability
    input: str
    context: ExecutorContext = Field(default_factory=ExecutorContext)

class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"

class ExecutorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    status: ExecutionStatus

    failure: str | None = None
    emitted_artifacts: dict[str, Any] = Field(default_factory=dict)

@runtime_checkable
class Executor(Protocol):
    """Structural boundary implemented by capability providers.\\
        **REQUIREMENTS:** 
        - Each Executor must define a class-level attribute `CAPABILITIES` 
        as a tuple of `Capability` instances that it can handle.
    """

    async def run(self, request: ExecutorRequest) -> ExecutorResult: ...


class PlannerWorkOutcome(BaseModel):
    """Minimal Planner-facing projection seam; Planner consumption is deferred."""

    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    status: ExecutionStatus
    semantic_summary: str
    authoritative_refs: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    permitted_next_actions: list[str] = Field(default_factory=list)
    result_digest: str


def normalize_for_planner(result: ExecutorResult) -> PlannerWorkOutcome:
    """Project only shared metadata; role-native payloads remain opaque to Planner."""

    # Exclude emitted_artifacts from the digest — it contains live RAM objects
    # that are not serializable and must not leak into the digest.
    serializable = result.model_dump(mode="json", exclude={"emitted_artifacts"})
    serialized = json.dumps(
        serializable,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    blocker = result.failure if result.failure is not None else None
    summary = (
        f"Work completed."
        if result.status == ExecutionStatus.SUCCEEDED else f"Work failed."
    )

    return PlannerWorkOutcome(
        task_id=result.task_id,
        status=result.status,
        semantic_summary=summary,
        blockers=[blocker] if blocker is not None else [],
        permitted_next_actions=(
            ["review_result"] if result.status == ExecutionStatus.SUCCEEDED else ["hold", "replan"]
        ),
        result_digest=hashlib.sha256(serialized).hexdigest(),
    )

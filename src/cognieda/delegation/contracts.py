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


class ExecutorInput(BaseModel):
    """Shared invocation input; semantic Task identity comes from project schemas."""

    model_config = ConfigDict(extra="forbid")

    task: Task


class ExecutorContext(BaseModel):
    """Small shared context that is safe for every registered executor."""

    model_config = ConfigDict(extra="forbid")

    dataset_path: str | None = None
    data_profile_id: UUID | None = None


class DEExecutorContext(ExecutorContext):
    """Extended context for the Data Explorer executor.

    Carries the RAM-resident DataProfile object directly (MVP only).
    In a persistence-backed phase this would be fetched by data_profile_id;
    for the RAM MVP we pass the live object to avoid a DB round-trip.

    # MVP NOTE: data_profile is a direct in-RAM reference.  It is intentionally
    # NOT stored inside ExecutionResult.  The pointer pattern below (in
    # ExecutionResult.emitted_artifacts) sends the UUID key, and the caller
    # retains the live object separately.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # In-memory DataFrame for the dataset.  Passed directly so the executor
    # does not need to re-read the file.
    dataframe: Any | None = None  # pd.DataFrame at runtime; typed Any to avoid heavy import
    # RAM-resident DataProfile, if already produced by a prior profiling pass.
    data_profile: Any | None = None  # DataProfile at runtime; typed Any to avoid circular import

class ExecutionRequest(BaseModel):
    """Typed capability request sent through the executor dispatcher."""

    model_config = ConfigDict(extra="forbid")

    capability: Capability
    input: SerializeAsAny[ExecutorInput]
    context: ExecutorContext = Field(default_factory=ExecutorContext)


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"

class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_role: str
    task_id: UUID
    work_id: str
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

    async def run(self, request: ExecutionRequest) -> ExecutionResult: ...


class PlannerWorkOutcome(BaseModel):
    """Minimal Planner-facing projection seam; Planner consumption is deferred."""

    model_config = ConfigDict(extra="forbid")

    source_role: str
    task_id: UUID
    work_id: str
    status: ExecutionStatus
    semantic_summary: str
    authoritative_refs: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    permitted_next_actions: list[str] = Field(default_factory=list)
    result_digest: str


def normalize_for_planner(result: ExecutionResult) -> PlannerWorkOutcome:
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
        f"{result.source_role} completed work {result.work_id}."
        if result.status == ExecutionStatus.SUCCEEDED
        else f"{result.source_role} could not complete work {result.work_id}."
    )

    return PlannerWorkOutcome(
        source_role=result.source_role,
        task_id=result.task_id,
        work_id=result.work_id,
        status=result.status,
        semantic_summary=summary,
        blockers=[blocker] if blocker is not None else [],
        permitted_next_actions=(
            ["review_result"] if result.status == ExecutionStatus.SUCCEEDED else ["hold", "replan"]
        ),
        result_digest=hashlib.sha256(serialized).hexdigest(),
    )

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import Task

from .capabilities import Capability


class ExecutorInput(BaseModel):
    """Shared invocation input; semantic Task identity comes from project schemas."""

    model_config = ConfigDict(extra="forbid")

    task: Task


class DataAnalysisOperation(StrEnum):
    """Finite deterministic operations admitted by the M3-A Data Explorer."""

    ROW_COUNT = "row_count"
    COLUMN_SUMMARY = "column_summary"
    MISSINGNESS = "missingness"
    VALUE_COUNTS = "value_counts"
    DESCRIPTIVE_STATISTICS = "descriptive_statistics"
    GROUP_SUMMARY = "group_summary"
    CORRELATION = "correlation"


class CorrelationMethod(StrEnum):
    PEARSON = "pearson"
    SPEARMAN = "spearman"


class DataAnalysisPlan(BaseModel):
    """Validated bounded parameters for one deterministic data operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: DataAnalysisOperation
    columns: tuple[str, ...] = Field(default=(), max_length=10)
    top_k: int | None = Field(default=None, ge=1, le=50)
    max_groups: int | None = Field(default=None, ge=1, le=50)
    correlation_method: CorrelationMethod | None = None

    @model_validator(mode="after")
    def _parameters_match_operation(self) -> DataAnalysisPlan:
        if any(not column.strip() for column in self.columns):
            raise ValueError("Analysis columns must be non-empty exact names.")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("Analysis columns must not contain duplicates.")

        expected_columns: int | tuple[int, int]
        if self.operation is DataAnalysisOperation.ROW_COUNT:
            expected_columns = 0
        elif self.operation in {
            DataAnalysisOperation.COLUMN_SUMMARY,
            DataAnalysisOperation.VALUE_COUNTS,
            DataAnalysisOperation.DESCRIPTIVE_STATISTICS,
        }:
            expected_columns = 1
        elif self.operation is DataAnalysisOperation.MISSINGNESS:
            expected_columns = (1, 10)
        elif self.operation is DataAnalysisOperation.GROUP_SUMMARY:
            expected_columns = 2
        else:
            expected_columns = (2, 10)

        if isinstance(expected_columns, int):
            valid_column_count = len(self.columns) == expected_columns
        else:
            valid_column_count = expected_columns[0] <= len(self.columns) <= expected_columns[1]
        if not valid_column_count:
            raise ValueError(
                f"{self.operation.value} received an invalid number of exact column names."
            )

        if (self.operation is DataAnalysisOperation.VALUE_COUNTS) != (self.top_k is not None):
            raise ValueError("top_k is required only for value_counts.")
        if (self.operation is DataAnalysisOperation.GROUP_SUMMARY) != (
            self.max_groups is not None
        ):
            raise ValueError("max_groups is required only for group_summary.")
        if (self.operation is DataAnalysisOperation.CORRELATION) != (
            self.correlation_method is not None
        ):
            raise ValueError("correlation_method is required only for correlation.")
        return self

    def bounded_parameters(self) -> dict[str, JsonValue]:
        """Return only the finite parameters that determine tool behavior."""

        parameters: dict[str, JsonValue] = {"columns": list(self.columns)}
        if self.top_k is not None:
            parameters["top_k"] = self.top_k
        if self.max_groups is not None:
            parameters["max_groups"] = self.max_groups
        if self.correlation_method is not None:
            parameters["correlation_method"] = self.correlation_method.value
        return parameters


class ExecutorContext(BaseModel):
    """Small shared context that is safe for every registered executor."""

    model_config = ConfigDict(extra="forbid")

    dataset_path: str | None = None
    data_profile_id: UUID | None = None
    analysis_plan: DataAnalysisPlan | None = None


class BaseState(BaseModel):
    """Shared graph state for graph-backed executor scaffolds."""

    model_config = ConfigDict(extra="forbid")

    task: Task
    messages: list[ModelMessage] = Field(default_factory=list)


class ExecutionRequest(BaseModel):
    """Typed capability request sent through the executor dispatcher."""

    model_config = ConfigDict(extra="forbid")

    capability: Capability
    input: ExecutorInput
    context: ExecutorContext = Field(default_factory=ExecutorContext)


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"


class ExecutionFailure(BaseModel):
    """Controlled provider failure; never represents fabricated success."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ExecutionResult(BaseModel):
    """Non-semantic transport metadata shared by role-native results."""

    model_config = ConfigDict(extra="forbid")

    source_role: str = Field(min_length=1)
    task_id: UUID
    work_id: str = Field(min_length=1)
    status: ExecutionStatus
    limitations: list[str] = Field(default_factory=list)
    failure: ExecutionFailure | None = None

    @model_validator(mode="after")
    def _failure_matches_status(self) -> ExecutionResult:
        if self.status == ExecutionStatus.SUCCEEDED and self.failure is not None:
            raise ValueError("A successful execution result cannot contain a failure.")
        if self.status != ExecutionStatus.SUCCEEDED and self.failure is None:
            raise ValueError("A blocked or failed execution result requires failure details.")
        return self


@runtime_checkable
class ExecutorProvider(Protocol):
    """Structural boundary implemented by capability providers."""

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
    limitations: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    permitted_next_actions: list[str] = Field(default_factory=list)
    result_digest: str


def normalize_for_planner(result: ExecutionResult) -> PlannerWorkOutcome:
    """Project only shared metadata; role-native payloads remain opaque to Planner."""

    serialized = json.dumps(
        result.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    blocker = result.failure.message if result.failure is not None else None
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
        limitations=list(result.limitations),
        blockers=[blocker] if blocker is not None else [],
        permitted_next_actions=(
            ["review_result"] if result.status == ExecutionStatus.SUCCEEDED else ["hold", "replan"]
        ),
        result_digest=hashlib.sha256(serialized).hexdigest(),
    )

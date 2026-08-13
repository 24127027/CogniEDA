from __future__ import annotations

from enum import StrEnum
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cognieda.execution import Capability, ExecutionResult, ExecutionStatus, ExecutorInput
from cognieda.schemas.artifacts import DataProfile


class DataAnalysisOperation(StrEnum):
    """Finite deterministic operations owned by the M3-A Data Explorer."""

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
    """Validated bounded parameters for one deterministic Data Explorer operation."""

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
        parameters: dict[str, JsonValue] = {"columns": list(self.columns)}
        if self.top_k is not None:
            parameters["top_k"] = self.top_k
        if self.max_groups is not None:
            parameters["max_groups"] = self.max_groups
        if self.correlation_method is not None:
            parameters["correlation_method"] = self.correlation_method.value
        return parameters


class DataAnalysisPlanningRequest(BaseModel):
    """Authoritative bounded context for Data Explorer operationalization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_instruction: str = Field(min_length=1)
    data_profile: DataProfile
    supported_operations: tuple[DataAnalysisOperation, ...] = tuple(DataAnalysisOperation)


class DataAnalysisPlannerPort(Protocol):
    """Data Explorer-owned boundary for Task instruction to bounded plan translation."""

    async def propose(self, request: DataAnalysisPlanningRequest) -> DataAnalysisPlan: ...


class DataExplorerInput(ExecutorInput):
    """Role-specific typed input carrying authoritative DataProfile planning context."""

    data_profile: DataProfile
    requested_work: str | None = Field(default=None, min_length=1)


class DataExplorerObservation(BaseModel):
    """Non-authoritative observation returned by bounded dataset work."""

    model_config = ConfigDict(extra="forbid")

    observation_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    payload: dict[str, JsonValue] = Field(min_length=1)
    artifact_refs: list[str] = Field(default_factory=list)


class DataExecutionProvenance(BaseModel):
    """Immutable lineage material for one explicit deterministic dataset operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_reference: str = Field(min_length=1)
    dataset_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    data_profile_id: UUID | None = None
    tool_reference: str = Field(min_length=1)
    operation: DataAnalysisOperation | Literal["dataset_profile"]
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    code_reference: str | None = Field(default=None, min_length=1)


class DataProfileCandidate(BaseModel):
    """Non-authoritative initial profile candidate without fabricated Task lineage."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_role: Literal["data_explorer"] = "data_explorer"
    work_id: str = Field(min_length=1)
    profile: DataProfile
    provenance: DataExecutionProvenance

    @model_validator(mode="after")
    def _requires_initial_profile_lineage(self) -> DataProfileCandidate:
        if self.provenance.operation != "dataset_profile":
            raise ValueError("A DataProfile candidate requires dataset_profile provenance.")
        if self.provenance.data_profile_id is not None:
            raise ValueError("An initial DataProfile candidate cannot claim prior authority.")
        return self


class DataExplorerResult(ExecutionResult):
    """Role-native Data Explorer output; drafts are not authoritative persistence."""

    capability: Capability
    observations: list[DataExplorerObservation] = Field(default_factory=list)
    produced_data_profile: DataProfile | None = None
    provenance: DataExecutionProvenance | None = None
    analysis_plan: DataAnalysisPlan | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    execution_details: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_data_capability(self) -> DataExplorerResult:
        if self.capability not in {
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
            Capability.DATA_TRANSFORMATION,
        }:
            raise ValueError("DataExplorerResult requires a Data Explorer capability.")
        if (
            self.status == ExecutionStatus.SUCCEEDED
            and not self.observations
            and self.produced_data_profile is None
        ):
            raise ValueError("A successful DataExplorerResult requires role-native output.")
        if self.status == ExecutionStatus.SUCCEEDED and self.provenance is None:
            raise ValueError("A successful DataExplorerResult requires execution provenance.")
        if (
            self.status == ExecutionStatus.SUCCEEDED
            and self.capability is Capability.DATA_ANALYSIS
            and self.analysis_plan is None
        ):
            raise ValueError("Successful DATA_ANALYSIS requires the validated role-native plan.")
        if self.capability is not Capability.DATA_ANALYSIS and self.analysis_plan is not None:
            raise ValueError("Only DATA_ANALYSIS may carry a DataAnalysisPlan.")
        if (
            self.capability == Capability.DATA_TRANSFORMATION
            and self.status == ExecutionStatus.SUCCEEDED
            and self.produced_data_profile is None
        ):
            raise ValueError("Successful transformation requires a successor DataProfile.")
        return self

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cognieda.execution import (
    Capability,
    DataAnalysisOperation,
    ExecutionResult,
    ExecutionStatus,
)
from cognieda.schemas.artifacts import DataProfile


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
            self.capability == Capability.DATA_TRANSFORMATION
            and self.status == ExecutionStatus.SUCCEEDED
            and self.produced_data_profile is None
        ):
            raise ValueError("Successful transformation requires a successor DataProfile.")
        return self

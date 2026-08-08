from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.artifacts import DataProfile

from ..capabilities import Capability
from ..types import ExecutionResult, ExecutionStatus


class DataExplorerObservation(BaseModel):
    """Non-authoritative observation returned by bounded dataset work."""

    model_config = ConfigDict(extra="forbid")

    observation_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list)


class DataExplorerResult(ExecutionResult):
    """Role-native Data Explorer output; drafts are not authoritative persistence."""

    capability: Capability
    observations: list[DataExplorerObservation] = Field(default_factory=list)
    produced_data_profile: DataProfile | None = None
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
        if (
            self.capability == Capability.DATA_TRANSFORMATION
            and self.status == ExecutionStatus.SUCCEEDED
            and self.produced_data_profile is None
        ):
            raise ValueError("Successful transformation requires a successor DataProfile.")
        return self

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai.messages import ModelMessage

from schemas.artifacts import DataProfile, Discovery, Evidence, Hypothesis, Task as ResearchTask

Task = ResearchTask

from .capabilities import CAPABILITY_IDS


class ExecutorInput(BaseModel):
    """Shared input for all executors"""

    model_config = ConfigDict(extra="forbid")

    task: Task
    ...


class ExecutorContext(BaseModel):
    """Shared context for all executors"""

    model_config = ConfigDict(extra="forbid")

    ...


class BaseState(BaseModel):
    """Base state for all executors"""

    task: Task
    messages: Sequence[ModelMessage] = Field(default_factory=tuple)


class ExecutionRequest(BaseModel):
    """Shared request for executor dispatch."""

    model_config = ConfigDict(extra="forbid")

    capability: str = Field(
        description="Executor capability id selected from the canonical capability catalog.",
        json_schema_extra={"enum": list(CAPABILITY_IDS)},
    )
    input: ExecutorInput
    context: ExecutorContext

    @field_validator("capability")
    @classmethod
    def validate_capability(cls, capability: str) -> str:
        if capability not in CAPABILITY_IDS:
            allowed = ", ".join(CAPABILITY_IDS)
            raise ValueError(
                f"Unknown executor capability: {capability}. Expected one of: {allowed}."
            )

        return capability


class ExecutorOutput(BaseModel):
    """PydanticAI output schema for executor-authored drafts."""

    model_config = ConfigDict(extra="ignore")

    hypothesis_draft: Hypothesis | None = Field(
        default=None,
        description="Hypothesis draft produced by the executor.",
    )
    evidence_drafts: list[dict[str, Any] | Evidence] = Field(
        default_factory=list,
        description="Evidence draft payloads proposed by the executor for planner review.",
    )
    evidence_draft: Evidence | None = Field(
        default=None,
        description="Single Evidence draft produced by bounded executor workflows.",
    )
    discovery_drafts: list[dict[str, Any] | Discovery] = Field(
        default_factory=list,
        description="Discovery draft payloads proposed by the executor for planner review.",
    )
    data_profile_draft: DataProfile | None = Field(
        default=None,
        description="Single DataProfile draft produced by bounded executor workflows.",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Evidence references supporting the execution result.",
    )
    execution_logs: list[str] = Field(
        default_factory=list,
        description="Execution logs intended for planner review.",
    )
    evaluation_outcome: str | None = Field(
        default=None,
        description="Raw statistical outcome from evidence evaluation.",
    )
    scientific_value: str | None = Field(
        default=None,
        description="Scientific value assessment for the execution outcome.",
    )
    execution_run_ref: str | None = Field(
        default=None,
        description="Optional provenance reference for the execution run that produced the drafts.",
    )
    final_result: dict[str, Any] | None = Field(
        default=None,
        description="Compact final envelope compiled by the executor graph.",
    )


class ExecutionResult(ExecutorOutput):
    """Validated result returned by an executor graph."""

    ...

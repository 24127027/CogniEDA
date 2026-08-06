from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_ai.messages import ModelMessage

from .capabilities import CAPABILITY_IDS


class Task(BaseModel):
    """Placeholder for a Task object.

    # TODO: Import the actual Task class later
    """


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
    

    # model_config = ConfigDict(extra="forbid")

    # evidence_drafts: list[dict[str, Any]] = Field(
    #     default_factory=list,
    #     description="Evidence draft payloads proposed by the executor for planner review.",
    # )
    # discovery_drafts: list[dict[str, Any]] = Field(
    #     default_factory=list,
    #     description="Discovery draft payloads proposed by the executor for planner review.",
    # )
    # execution_run_ref: str | None = Field(
    #     default=None,
    #     description="Optional provenance reference for the execution run that produced the drafts.",
    # )


class ExecutionResult(ExecutorOutput):
    """Validated result returned by an executor graph."""

    ...

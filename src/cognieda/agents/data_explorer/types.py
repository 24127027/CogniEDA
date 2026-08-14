"""Types for the Data Explorer LangGraph workflow."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from cognieda.schemas.artifacts import DataProfile, Evidence


# ---------------------------------------------------------------------------
# Workflow step models
# ---------------------------------------------------------------------------


class ExecutionType(StrEnum):
    BUILTIN_TOOL = "builtin_tool"
    CODE_GENERATION = "code_generation"


class StepStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AnalysisStep(BaseModel):
    """One bounded step in the DE planning output."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    target_columns: list[str] = Field(default_factory=list)
    execution_type: ExecutionType
    # Populated only when execution_type is BUILTIN_TOOL
    builtin_tool_name: str | None = None
    # Keyword arguments to pass to the builtin tool (e.g. {"bins": 20, "method": "iqr"})
    builtin_tool_kwargs: dict[str, Any] = Field(default_factory=dict)
    # Populated only when execution_type is CODE_GENERATION
    generated_code: str | None = None
    # The Python type name the executor should validate against, e.g. "dict", "float"
    expected_output_type: str = Field(min_length=1)


class StepResult(BaseModel):
    """Observed output for one executed step, including provenance material."""

    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    status: StepStatus
    output_payload: dict[str, Any] = Field(default_factory=dict)
    # Column names accessed during execution
    variables_accessed: list[str] = Field(default_factory=list)
    # Scalar values observed (e.g. row counts, min/max) for provenance
    values_observed: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    retry_count: int = 0


# ---------------------------------------------------------------------------
# Planning output from the model
# ---------------------------------------------------------------------------


class PlanningOutput(BaseModel):
    """Structured plan produced by the Pydantic AI planning agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    steps: list[AnalysisStep] = Field(min_length=1)
    rationale: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Evaluation output from the model
# ---------------------------------------------------------------------------


class EvaluationVerdict(StrEnum):
    SATISFIED = "satisfied"
    NEEDS_REVISION = "needs_revision"
    UNFEASIBLE = "unfeasible"


class EvaluationOutput(BaseModel):
    """Structured evaluation from the Pydantic AI check-result agent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: EvaluationVerdict
    # Human-readable summary of what was gathered
    summary: str = Field(min_length=1)
    # Sent back to planning when verdict is NEEDS_REVISION
    revision_feedback: str | None = None


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------


class State(BaseModel):
    """Transient state threaded across the three DE graph nodes."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # ---- Input context -------------------------------------------------------
    task_id: UUID
    objective_id: UUID | None = None
    task_instruction: str = Field(min_length=1)
    dataset_path: str = Field(min_length=1)
    dataset_digest: str = Field(min_length=1)
    # Authoritative DataProfile; may be None for profiling tasks
    data_profile: DataProfile | None = None

    # ---- Workflow state ------------------------------------------------------
    plan: list[AnalysisStep] = Field(default_factory=list)
    execution_results: list[StepResult] = Field(default_factory=list)
    # Feedback injected by check_result when sending back to planning
    revision_feedback: str | None = None
    iteration: int = 0
    max_iterations: int = 3

    # ---- Output objects (set at most once, by check_result) ------------------
    emitted_evidence: Evidence | None = None
    emitted_data_profile: DataProfile | None = None

    # ---- Terminal status -----------------------------------------------------
    workflow_status: Literal["pending", "succeeded", "failed", "blocked"] = "pending"
    failure_reason: str | None = None


# ---------------------------------------------------------------------------
# Error taxonomy
# ---------------------------------------------------------------------------


class DEErrorCode(StrEnum):
    PLANNING_FAILED = "planning_failed"
    EXECUTION_FAILED = "execution_failed"
    EVALUATION_FAILED = "evaluation_failed"
    MAX_ITERATIONS_EXCEEDED = "max_iterations_exceeded"
    EVIDENCE_CONSTRUCTION_FAILED = "evidence_construction_failed"
    PROFILE_CONSTRUCTION_FAILED = "profile_construction_failed"
    UNFEASIBLE_REQUEST = "unfeasible_request"
    INVALID_INPUT = "invalid_input"


class DEControlledError(BaseModel):
    """Application-facing failure that does not leak arbitrary exception detail."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: DEErrorCode
    message: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Final application-facing output
# ---------------------------------------------------------------------------


class DataExplorerOutput(BaseModel):
    """Strongly typed result of one complete Data Explorer invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: UUID
    # Exactly one of the two output objects is populated on success
    evidence: Evidence | None = None
    data_profile: DataProfile | None = None
    # Human-readable summary of what was done
    summary: str = Field(min_length=1)
    error: DEControlledError | None = None


__all__ = (
    "AnalysisStep",
    "DEControlledError",
    "DEErrorCode",
    "DataExplorerOutput",
    "EvaluationOutput",
    "EvaluationVerdict",
    "ExecutionType",
    "PlanningOutput",
    "State",
    "StepResult",
    "StepStatus",
)

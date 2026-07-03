"""Executor-specific graph contracts for hypothesis analysis."""

from __future__ import annotations

from pydantic import Field

from agents.types import AgentEnvelope, BaseState
from schemas.artifacts import Discovery, Evidence


class ExecutorInput(AgentEnvelope):
    """Input accepted by an executor.

    Conclusion context must be prepared upstream without assumptions.
    """

    hypothesis_id: str
    profile_id: str
    analysis_frame_ref: str
    conclusion_context: str | None = None


class ExecutorOutput(AgentEnvelope):
    """Executor output may contain Evidence and Discovery drafts."""

    evidence_drafts: list[Evidence] = Field(default_factory=list)
    discovery_drafts: list[Discovery] = Field(default_factory=list)
    execution_run_ref: str | None = None


class ExecutorState(BaseState):
    """Internal executor state."""

    input: ExecutorInput | None = None
    output: ExecutorOutput | None = None

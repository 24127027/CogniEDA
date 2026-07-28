"""Internal state for HypothesisAnalyst executor.

This state NEVER leaves the executor.
It's converted from ExecutionRequest on entry and to ExecutionResult on exit.
"""

from pydantic import Field

from ..types import BaseState


class State(BaseState):
    """State for the Hypothesis Analyst agent.

    Internal state fields for hypothesis analysis workflow.
    This will expand as graph implementation progresses.
    """

    hypothesis_statement: str | None = None
    statistical_method: str | None = None
    method_candidates: list[str] = Field(
        default_factory=lambda: [
            "placeholder_statistical_test",
            "fallback_nonparametric_test",
        ]
    )
    assumption_checks: list[str] = Field(default_factory=list)
    workflow_notes: list[str] = Field(default_factory=list)
    supporting_metrics_ready: bool = False
    needs_data_exploration: bool = False
    assumption_failed: bool = False
    test_result_summary: str | None = None
    execution_run_ref: str | None = None
    evidence_drafts: list[dict[str, object]] = Field(default_factory=list)
    discovery_drafts: list[dict[str, object]] = Field(default_factory=list)
    error_message: str | None = None

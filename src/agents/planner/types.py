"""Planner-specific graph contracts."""

from __future__ import annotations

from pydantic import Field

from agents.types import AgentEnvelope, BaseState


class PlannerInput(AgentEnvelope):
    """Input accepted by the Planner orchestrator."""

    user_request: str
    planning_context: str | None = None


class PlannerOutput(AgentEnvelope):
    """Planner output: operations and routing, not scientific knowledge."""

    route: str | None = None
    planner_operations: list[str] = Field(default_factory=list)
    executor_dispatch_ref: str | None = None


class PlannerState(BaseState):
    """Internal Planner state."""

    input: PlannerInput | None = None
    output: PlannerOutput | None = None
    pending_operations: list[str] = Field(default_factory=list)

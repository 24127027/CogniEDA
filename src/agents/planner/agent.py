"""Planner agent wrapper."""

from __future__ import annotations

from agents.base_agent import BaseAgent

from .graph import build_graph
from .types import PlannerInput, PlannerOutput, PlannerState


class Planner(BaseAgent[PlannerInput, PlannerOutput, PlannerState]):
    """Planner orchestrator. It produces operations, not Evidence or Discovery."""

    def __init__(self) -> None:
        super().__init__(graph=build_graph())

    async def before_run(self, input: PlannerInput) -> PlannerState:
        raise NotImplementedError("Planner.before_run is not implemented yet.")

    async def after_run(self, output: PlannerState) -> PlannerOutput:
        raise NotImplementedError("Planner.after_run is not implemented yet.")

"""Hypothesis-analysis executor wrapper."""

from __future__ import annotations

from agents.base_agent import BaseAgent

from .graph import build_graph
from .types import ExecutorInput, ExecutorOutput, ExecutorState


class HypothesisAnalyst(BaseAgent[ExecutorInput, ExecutorOutput, ExecutorState]):
    """Executor that can produce Evidence and Discovery drafts."""

    def __init__(self) -> None:
        super().__init__(graph=build_graph())

    async def before_run(self, input: ExecutorInput) -> ExecutorState:
        raise NotImplementedError("HypothesisAnalyst.before_run is not implemented yet.")

    async def after_run(self, output: ExecutorState) -> ExecutorOutput:
        raise NotImplementedError("HypothesisAnalyst.after_run is not implemented yet.")

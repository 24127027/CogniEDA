"""Graph-miner agent wrapper."""

from __future__ import annotations

from agents.base_agent import BaseAgent

from .graph import build_graph
from .types import GraphMinerInput, GraphMinerOutput, GraphMinerState


class GraphMiner(BaseAgent[GraphMinerInput, GraphMinerOutput, GraphMinerState]):
    """Infrastructure agent for graph search."""

    def __init__(self) -> None:
        super().__init__(graph=build_graph())

    async def before_run(self, input: GraphMinerInput) -> GraphMinerState:
        raise NotImplementedError("GraphMiner.before_run is not implemented yet.")

    async def after_run(self, output: GraphMinerState) -> GraphMinerOutput:
        raise NotImplementedError("GraphMiner.after_run is not implemented yet.")

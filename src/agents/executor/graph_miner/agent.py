"""Deferred Graph Miner wrapper."""

from __future__ import annotations

from tools.builtin import AvailableBuiltinTools

from ..capabilities import Capability
from ..types import ExecutionRequest, ExecutionResult


class GraphMiner:
    """Import-safe scaffold; S0 does not register the unimplemented graph."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = (AvailableBuiltinTools.GRAPH,)

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        if request.capability != Capability.GRAPH_MINING:
            raise ValueError(f"Graph Miner cannot provide {request.capability}.")
        raise NotImplementedError("Graph Miner runtime is deferred beyond S0.")


GraphMinerExecutor = GraphMiner

__all__ = ("GraphMiner", "GraphMinerExecutor")

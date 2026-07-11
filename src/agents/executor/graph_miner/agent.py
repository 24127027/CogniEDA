"""Graph-miner agent wrapper."""

from __future__ import annotations

from ..capabilities import Capability
from ..executor import Executor
from ..registry import executor_registry
from .graph import build_graph
from .state import State


@executor_registry.register(Capability.GRAPH_MINING)
class GraphMiner(Executor[State]):
    """Infrastructure agent for graph search."""

    def __init__(self) -> None:
        super().__init__(build_graph)


GraphMinerExecutor = GraphMiner

__all__ = ("GraphMiner", "GraphMinerExecutor")

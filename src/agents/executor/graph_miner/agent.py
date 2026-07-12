"""Graph-miner agent wrapper."""

from __future__ import annotations

from tools.builtin_tools import AvailableBuiltinTools

from ..capabilities import Capability
from ..executor import Executor
from ..registry import executor_registry
from .graph import build_graph
from .state import State


@executor_registry.register(Capability.GRAPH_MINING)
class GraphMiner(Executor[State]):
    """Infrastructure agent for graph search."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = (AvailableBuiltinTools.GRAPH,)

    def __init__(self) -> None:
        super().__init__(build_graph)


GraphMinerExecutor = GraphMiner

__all__ = ("GraphMiner", "GraphMinerExecutor")

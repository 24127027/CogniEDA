"""Graph-miner agent wrapper."""

from __future__ import annotations

from ..executor import Executor

from .graph import build_graph
from .state import State

class GraphMiner(Executor[State]):
    """Infrastructure agent for graph search."""

    def __init__(self) -> None:
        super().__init__(build_graph)

    

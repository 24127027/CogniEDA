"""Graph-miner agent wrapper kept outside Data Explorer dispatch."""

from __future__ import annotations

from tools.builtin_tools import AvailableBuiltinTools


class GraphMiner:
    """Infrastructure agent for graph search (unimplemented target-only facade)."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = (AvailableBuiltinTools.GRAPH,)

    def __init__(self) -> None:
        raise NotImplementedError("GraphMiner graph is not implemented yet.")


__all__ = ("GraphMiner",)

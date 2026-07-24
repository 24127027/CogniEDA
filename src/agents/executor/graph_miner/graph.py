from typing import Any

from langgraph.graph.state import CompiledStateGraph

from ..types import ExecutorContext, ExecutorInput
from .state import State


def build_graph() -> CompiledStateGraph[State, ExecutorContext, ExecutorInput, Any]:
    """Build the GraphMiner graph."""

    raise NotImplementedError("GraphMiner graph is not implemented yet.")

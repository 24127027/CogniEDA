from langgraph.graph.state import CompiledStateGraph

from ..types import ExecutionResult, ExecutorContext, ExecutorInput
from .state import State


def build_graph() -> CompiledStateGraph[State, ExecutorContext, ExecutorInput, ExecutionResult]:
    """Build the GraphMiner graph."""

    raise NotImplementedError("GraphMiner graph is not implemented yet.")

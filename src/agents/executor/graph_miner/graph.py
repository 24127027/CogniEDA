from langgraph.graph.state import CompiledStateGraph

from application.orchestrator.execution_contracts import ExecutorResult

from ..types import ExecutorContext, ExecutorInput
from .state import State


def build_graph() -> CompiledStateGraph[State, ExecutorContext, ExecutorInput, ExecutorResult]:
    """Build the GraphMiner graph."""

    raise NotImplementedError("GraphMiner graph is not implemented yet.")

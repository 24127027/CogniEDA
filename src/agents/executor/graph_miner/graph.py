from langgraph.graph.state import CompiledStateGraph
from ..types import Input, Context
from .state import State

def build_graph() -> CompiledStateGraph[State, Context, Input, State]:
    """Build the GraphMiner graph."""

    raise NotImplementedError("GraphMiner graph is not implemented yet.")
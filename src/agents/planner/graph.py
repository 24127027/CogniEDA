from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .nodes import R, registry
from .types import Context, State


def build_graph() -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(
        State,
        context_schema=Context,
    )

    for name, func in registry.nodes.items():
        builder.add_node(name, func)

    builder.add_edge(
        START,
        R.create_plan,
    )

    builder.add_edge(
        R.create_plan,
        END,
    )

    return builder.compile()
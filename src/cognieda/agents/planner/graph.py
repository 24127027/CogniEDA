from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .context import Context
from .nodes import compose_response, prepare_results, understand_request
from .types import State


def build_graph() -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(
        State,
        context_schema=Context,
    )

    builder.add_node("understand_request", understand_request)
    builder.add_node("prepare_results", prepare_results)
    builder.add_node("compose_response", compose_response)

    builder.add_edge(START, "understand_request")
    builder.add_edge("understand_request", "prepare_results")
    builder.add_edge("prepare_results", "compose_response")
    builder.add_edge("compose_response", END)

    return builder.compile()

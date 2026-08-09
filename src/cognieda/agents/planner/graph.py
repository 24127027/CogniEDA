from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .nodes import apply_planning_state, compose_response, dispatch_work, understand_request
from .types import Context, State


def build_graph() -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(
        State,
        context_schema=Context,
    )

    builder.add_node("understand_request", understand_request)
    builder.add_node("apply_planning_state", apply_planning_state)
    builder.add_node("dispatch_work", dispatch_work)
    builder.add_node("compose_response", compose_response)

    builder.add_edge(START, "understand_request")
    builder.add_edge("understand_request", "apply_planning_state")
    builder.add_edge("apply_planning_state", "dispatch_work")
    builder.add_edge("dispatch_work", "compose_response")
    builder.add_edge("compose_response", END)

    return builder.compile()

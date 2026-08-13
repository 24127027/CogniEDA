from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .context import PlannerGraphContext
from .nodes import compose_response, prepare_results, understand_request
from .state import PlannerState


def build_graph() -> CompiledStateGraph[
    PlannerState, PlannerGraphContext, PlannerState, PlannerState
]:
    builder = StateGraph(
        PlannerState,
        context_schema=PlannerGraphContext,
    )

    builder.add_node("understand_request", understand_request)
    builder.add_node("prepare_results", prepare_results)
    builder.add_node("compose_response", compose_response)

    builder.add_edge(START, "understand_request")
    builder.add_edge("understand_request", "prepare_results")
    builder.add_edge("prepare_results", "compose_response")
    builder.add_edge("compose_response", END)

    return builder.compile()

from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .context import PlannerGraphContext
from .nodes import compose_authoritative_answer, route_after_planner, run_planner
from .state import PlannerState


def build_graph() -> CompiledStateGraph[
    PlannerState, PlannerGraphContext, PlannerState, PlannerState
]:
    builder = StateGraph(
        PlannerState,
        context_schema=PlannerGraphContext,
    )

    builder.add_node("run_planner", run_planner)
    builder.add_node("compose_authoritative_answer", compose_authoritative_answer)

    builder.add_edge(START, "run_planner")
    builder.add_conditional_edges(
        "run_planner",
        route_after_planner,
        {
            "compose_authoritative_answer": "compose_authoritative_answer",
            END: END,
        },
    )
    builder.add_edge("compose_authoritative_answer", END)

    return builder.compile()

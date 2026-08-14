from __future__ import annotations

from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .state import PlannerState


def route_after_plan(state: PlannerState) -> Literal["execute", "__end__"]:
    """Pause at execute only for a complete candidate Plan bundle."""

    if state.cognitive_result is not None and state.cognitive_result.plan is not None:
        return "execute"
    return "__end__"


def route_after_execute(state: PlannerState) -> Literal["plan", "__end__"]:
    """Return to planning after explicit rejection/revision or an execution replan."""

    if state.approved_plan_id is None and state.human_feedback is not None:
        return "plan"
    if (
        state.cognitive_result is not None
        and state.cognitive_result.replan_reason is not None
    ):
        return "plan"
    return "__end__"


def build_graph(
    plan_node: Any,
    execute_node: Any,
) -> CompiledStateGraph[PlannerState, None, PlannerState, PlannerState]:
    """Compile the two cognitive Planner nodes with a resumable Human boundary."""

    builder = StateGraph(PlannerState)
    builder.add_node("plan", plan_node)
    builder.add_node("execute", execute_node)

    builder.add_edge(START, "plan")
    builder.add_conditional_edges(
        "plan",
        route_after_plan,
        {"execute": "execute", END: END},
    )
    builder.add_conditional_edges(
        "execute",
        route_after_execute,
        {"plan": "plan", END: END},
    )

    return builder.compile(checkpointer=InMemorySaver())


__all__ = ("build_graph", "route_after_execute", "route_after_plan")

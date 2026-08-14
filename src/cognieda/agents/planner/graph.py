from __future__ import annotations

from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .state import PlannerState


def route_after_plan_or_answer(state: PlannerState) -> Literal["execute", "__end__"]:
    """Execute new or continuing approved work; otherwise return to the Human."""

    if state.result is not None and (
        state.result.plan is not None or state.result.continue_execution
    ):
        return "execute"
    return "__end__"


def build_graph(
    plan_or_answer_node: Any,
    execute_node: Any,
) -> CompiledStateGraph[PlannerState, None, PlannerState, PlannerState]:
    """Compile the two cognitive Planner nodes with a resumable Human boundary."""

    builder = StateGraph(PlannerState)
    builder.add_node("plan_or_answer", plan_or_answer_node)
    builder.add_node("execute", execute_node)

    builder.add_edge(START, "plan_or_answer")
    builder.add_conditional_edges(
        "plan_or_answer",
        route_after_plan_or_answer,
        {"execute": "execute", END: END},
    )
    builder.add_edge("execute", "plan_or_answer")

    return builder.compile(checkpointer=InMemorySaver())


__all__ = ("build_graph", "route_after_plan_or_answer")

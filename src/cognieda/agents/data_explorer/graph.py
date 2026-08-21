"""LangGraph graph builder for the Data Explorer workflow."""

from __future__ import annotations

from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from .context import Context
from .nodes import check_result, execute, planning
from .types import State


def _route_after_check_result(state: State) -> str:
    """Conditional edge: return to planning or end the graph."""
    if state.workflow_status in ("succeeded", "failed", "blocked"):
        return END
    # revision_feedback set and iteration budget remaining: loop back to planning
    return "planning"


def build_graph() -> CompiledStateGraph[State, Context, State, State]:
    builder = StateGraph(
        State,
        context_schema=Context,
    )

    builder.add_node("planning", planning)
    builder.add_node("execute", execute)
    builder.add_node("check_result", check_result)

    builder.add_edge(START, "planning")
    builder.add_edge("planning", "execute")
    builder.add_edge("execute", "check_result")

    builder.add_conditional_edges(
        "check_result",
        _route_after_check_result,
        {
            "planning": "planning",
            END: END,
        },
    )

    return builder.compile()


__all__ = ("build_graph",)

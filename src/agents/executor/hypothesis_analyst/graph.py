from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from ..types import ExecutionResult, ExecutorContext, ExecutorInput
from .nodes import (
    choose_statistical_method,
    draft_discovery_candidate,
    execute_statistical_test,
    formalize_hypothesis,
    interpret_results,
    log_mismatch_and_exit,
    request_data_exploration,
    route_after_formalize,
    route_after_assumptions,
    route_after_method,
    route_after_results,
    verify_statistical_assumptions,
)
from .state import State


def build_graph() -> CompiledStateGraph[State, ExecutorContext, ExecutorInput, ExecutionResult]:
    """Build the Hypothesis Analyst execution workflow."""

    builder = StateGraph(State, context_schema=ExecutorContext)

    builder.add_node("formalize_hypothesis", formalize_hypothesis)
    builder.add_node("choose_statistical_method", choose_statistical_method)
    builder.add_node("verify_statistical_assumptions", verify_statistical_assumptions)
    builder.add_node("request_data_exploration", request_data_exploration)
    builder.add_node("execute_statistical_test", execute_statistical_test)
    builder.add_node("interpret_results", interpret_results)
    builder.add_node("draft_discovery_candidate", draft_discovery_candidate)
    builder.add_node("log_mismatch_and_exit", log_mismatch_and_exit)

    builder.add_edge(START, "formalize_hypothesis")

    builder.add_conditional_edges(
        "formalize_hypothesis",
        route_after_formalize,
        {
            "choose_statistical_method": "choose_statistical_method",
            "log_mismatch_and_exit": "log_mismatch_and_exit",
        },
    )

    builder.add_conditional_edges(
        "choose_statistical_method",
        route_after_method,
        {
            "verify_statistical_assumptions": "verify_statistical_assumptions",
            "log_mismatch_and_exit": "log_mismatch_and_exit",
        },
    )

    builder.add_conditional_edges(
        "verify_statistical_assumptions",
        route_after_assumptions,
        {
            "request_data_exploration": "request_data_exploration",
            "execute_statistical_test": "execute_statistical_test",
            "choose_statistical_method": "choose_statistical_method",
            "log_mismatch_and_exit": "log_mismatch_and_exit",
        },
    )

    builder.add_edge("request_data_exploration", "verify_statistical_assumptions")
    builder.add_edge("execute_statistical_test", "interpret_results")

    builder.add_conditional_edges(
        "interpret_results",
        route_after_results,
        {
            "draft_discovery_candidate": "draft_discovery_candidate",
            "log_mismatch_and_exit": "log_mismatch_and_exit",
        },
    )

    builder.add_edge("draft_discovery_candidate", END)
    builder.add_edge("log_mismatch_and_exit", END)

    return builder.compile()

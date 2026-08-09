from __future__ import annotations

from functools import partial

from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from cognieda.application.ports import AgentFactoryPort, ModelConfig

from .deps import AdmissionCall, DispatcherCall
from .nodes import (
    assess_scientific_value,
    compile_result,
    dispatch_to_de,
    evaluate_evidence,
    formulate_hypothesis,
    handle_failure_and_logs,
    plan_de_requests,
    request_admission,
)
from .state import State


def build_graph(
    *,
    config: ModelConfig,
    agent_factory: AgentFactoryPort | None,
    mock_dispatcher_call: DispatcherCall,
    mock_admission_call: AdmissionCall,
) -> CompiledStateGraph[State, None, State, State]:
    builder = StateGraph(State)

    builder.add_node(
        "formulate_hypothesis",
        partial(
            formulate_hypothesis,
            agent_config=config,
            agent_factory=agent_factory,
        ),
    )
    builder.add_node(
        "plan_de_requests",
        partial(plan_de_requests, mock_dispatcher_call=mock_dispatcher_call),
    )
    builder.add_node(
        "dispatch_to_de",
        partial(dispatch_to_de, mock_dispatcher_call=mock_dispatcher_call),
    )
    builder.add_node(
        "evaluate_evidence",
        partial(
            evaluate_evidence,
            agent_config=config,
            agent_factory=agent_factory,
        ),
    )
    builder.add_node("assess_scientific_value", assess_scientific_value)
    builder.add_node(
        "request_admission",
        partial(request_admission, mock_admission_call=mock_admission_call),
    )
    builder.add_node("handle_failure_and_logs", handle_failure_and_logs)
    builder.add_node("compile_result", compile_result)

    builder.add_edge(START, "formulate_hypothesis")
    builder.add_conditional_edges(
        "formulate_hypothesis",
        lambda state: (
            "plan_de_requests"
            if state["hypothesis_draft"] is not None
            else "handle_failure_and_logs"
        ),
        {
            "plan_de_requests": "plan_de_requests",
            "handle_failure_and_logs": "handle_failure_and_logs",
        },
    )
    builder.add_conditional_edges(
        "plan_de_requests",
        lambda state: (
            "dispatch_to_de" if state["de_capability_requests"] else "handle_failure_and_logs"
        ),
        {
            "dispatch_to_de": "dispatch_to_de",
            "handle_failure_and_logs": "handle_failure_and_logs",
        },
    )
    builder.add_conditional_edges(
        "dispatch_to_de",
        lambda state: "evaluate_evidence" if state["collected_evidence"] else "plan_de_requests",
        {
            "evaluate_evidence": "evaluate_evidence",
            "plan_de_requests": "plan_de_requests",
        },
    )
    builder.add_edge("evaluate_evidence", "assess_scientific_value")
    builder.add_conditional_edges(
        "assess_scientific_value",
        lambda state: (
            "request_admission"
            if state["scientific_value"] == "valuable knowledge"
            else "compile_result"
        ),
        {
            "request_admission": "request_admission",
            "compile_result": "compile_result",
        },
    )
    builder.add_conditional_edges(
        "request_admission",
        lambda state: (
            "compile_result" if state["discovery_draft"] is not None else "handle_failure_and_logs"
        ),
        {
            "compile_result": "compile_result",
            "handle_failure_and_logs": "handle_failure_and_logs",
        },
    )
    builder.add_edge("handle_failure_and_logs", "compile_result")
    builder.add_edge("compile_result", END)

    return builder.compile()

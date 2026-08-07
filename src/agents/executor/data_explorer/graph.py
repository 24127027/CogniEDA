from __future__ import annotations

from functools import partial

from langgraph.graph import END, START
from langgraph.graph.state import CompiledStateGraph, StateGraph

from agents.llm import ModelConfig

from ..types import ExecutionResult, ExecutorContext, ExecutorInput
from .nodes import (
    compile_result,
    evaluate_results,
    execute_profiling_and_cleaning,
    generate_and_execute_code,
    handle_failure_and_logs,
	route_results,
    route_request,
)
from .state import State


def build_graph(
	*,
	config: ModelConfig,
) -> CompiledStateGraph[State, ExecutorContext, ExecutorInput, ExecutionResult]:
	builder = StateGraph(State)

	builder.add_node(
		"generate_and_execute_code",
		partial(generate_and_execute_code, agent_config=config),
	)
	builder.add_node("evaluate_results", evaluate_results)
	builder.add_node(
		"execute_profiling_and_cleaning",
		partial(execute_profiling_and_cleaning, agent_config=config),
	)
	builder.add_node("handle_failure_and_logs", handle_failure_and_logs)
	builder.add_node("compile_result", compile_result)

	builder.add_conditional_edges(
		START,
		route_request,
		{
			"generate_and_execute_code": "generate_and_execute_code",
			"execute_profiling_and_cleaning": "execute_profiling_and_cleaning",
		},
	)

	builder.add_edge("generate_and_execute_code", "evaluate_results")
	builder.add_conditional_edges(
		"evaluate_results",
		route_results,
		{
			"compile_result": "compile_result",
			"generate_and_execute_code": "generate_and_execute_code",
			"handle_failure_and_logs": "handle_failure_and_logs",
		},
	)

	builder.add_edge("execute_profiling_and_cleaning", "compile_result")

	builder.add_edge("handle_failure_and_logs", "compile_result")
	builder.add_edge("compile_result", END)

	return builder.compile()
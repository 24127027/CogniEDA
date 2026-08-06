from __future__ import annotations

import asyncio

from agents.executor import ExecutorContext, ExecutorInput, Task
from agents.executor.hypothesis_analyst.agent import HypothesisAnalyst
from agents.executor.hypothesis_analyst.nodes import (
    choose_statistical_method,
    route_after_assumptions,
    verify_statistical_assumptions,
)
from agents.executor.hypothesis_analyst.state import State
from agents.executor.hypothesis_analyst.graph import build_graph


def test_hypothesis_analyst_graph_builds() -> None:
    graph = build_graph()

    assert graph is not None


def test_hypothesis_analyst_executor_runs_new_workflow() -> None:
    executor = HypothesisAnalyst()

    result = asyncio.run(executor.run(ExecutorInput(task=Task()), ExecutorContext()))

    assert result.execution_run_ref == "execution-run:hypothesis-analyst"
    assert result.evidence_drafts
    assert result.discovery_drafts


def test_hypothesis_analyst_assumption_failure_loops_back_to_method_selection() -> None:
    state = State(task=Task())

    choose_statistical_method(state, None)
    state.supporting_metrics_ready = True
    verify_statistical_assumptions(state, None)

    assert state.assumption_failed is True
    assert route_after_assumptions(state, None) == "choose_statistical_method"
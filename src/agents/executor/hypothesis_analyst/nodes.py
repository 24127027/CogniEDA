from __future__ import annotations

from typing import Literal

from langgraph.runtime import Runtime

from ..types import ExecutorContext
from .state import State


def formalize_hypothesis(state: State, runtime: Runtime[ExecutorContext]) -> State:
    state.hypothesis_statement = (
        "Test the assigned analytical claim using the current scaffolded data context."
    )
    state.workflow_notes.append("Formalized the hypothesis from the incoming task.")
    return state


def route_after_formalize(
    state: State,
    runtime: Runtime[ExecutorContext],
) -> Literal["not_testable", "is_testable"]:
    if state.error_message is not None:
        return "not_testable"
    return "is_testable"


def choose_statistical_method(state: State, runtime: Runtime[ExecutorContext]) -> State:
    if not state.method_candidates:
        state.error_message = "No statistical methods remain for the current hypothesis."
        state.workflow_notes.append("No statistical method candidates remained.")
        return state

    state.statistical_method = state.method_candidates.pop(0)
    state.assumption_failed = False
    state.workflow_notes.append(
        f"Selected statistical method: {state.statistical_method}."
    )
    return state


def route_after_method(
    state: State,
    runtime: Runtime[ExecutorContext],
) -> Literal["no_candidates_left", "has_candidates"]:
    if state.error_message is not None:
        return "no_candidates_left"
    return "has_candidates"


def verify_statistical_assumptions(state: State, runtime: Runtime[ExecutorContext]) -> State:
    state.assumption_checks.append("assumptions_reviewed")
    if not state.supporting_metrics_ready:
        state.needs_data_exploration = True
        state.assumption_failed = False
        state.workflow_notes.append(
            "Checked the method assumptions and flagged missing supporting metrics."
        )
        return state

    state.needs_data_exploration = False
    if state.statistical_method == "placeholder_statistical_test":
        state.assumption_failed = True
        state.workflow_notes.append(
            "Current method failed its assumptions; another method is needed."
        )
        return state

    state.assumption_failed = False
    state.workflow_notes.append("Method assumptions passed with the current data profile.")
    return state


def request_data_exploration(state: State, runtime: Runtime[ExecutorContext]) -> State:
    state.workflow_notes.append("Requested supporting data exploration before execution.")
    state.supporting_metrics_ready = True
    state.needs_data_exploration = False
    return state


def route_after_data_exploration(
    state: State,
    runtime: Runtime[ExecutorContext],
) -> Literal["dispatcher_data_exploration"]:
    return "dispatcher_data_exploration"


def execute_statistical_test(state: State, runtime: Runtime[ExecutorContext]) -> State:
    state.execution_run_ref = "execution-run:hypothesis-analyst"
    state.evidence_drafts = [
        {
            "analysis_frame_ref": "analysis-frame:hypothesis-analyst",
            "execution_run_ref": state.execution_run_ref,
            "method": state.statistical_method,
            "result_summary": {
                "summary": "Scaffold execution completed with placeholder statistical output.",
                "key_findings": ["Result is ready for planner review."],
            },
        }
    ]
    state.workflow_notes.append("Executed the statistical test and prepared Evidence drafts.")
    return state


def interpret_results(state: State, runtime: Runtime[ExecutorContext]) -> State:
    state.test_result_summary = (
        "Placeholder result interpretation completed for the hypothesis analysis flow."
    )
    state.workflow_notes.append("Interpreted the execution output.")
    return state


def draft_discovery_candidate(state: State, runtime: Runtime[ExecutorContext]) -> State:
    state.discovery_drafts = [
        {
            "hypothesis_statement": state.hypothesis_statement,
            "claim": {
                "statement": "The placeholder hypothesis was reviewed and can be drafted for review.",
                "scope": "scaffold execution only",
            },
            "validity_basis": {
                "analysis_frame_refs": ["analysis-frame:hypothesis-analyst"],
                "evidence_ids": ["evidence-draft:placeholder"],
                "hypothesis_id": "hypothesis:placeholder",
                "method": state.statistical_method,
                "decision_rule": "planner review required",
                "assumptions_excluded_from_inference": True,
            },
        }
    ]
    state.workflow_notes.append("Prepared a Discovery draft candidate for planner review.")
    return state


def log_mismatch_and_exit(state: State, runtime: Runtime[ExecutorContext]) -> State:
    if state.error_message is None:
        state.error_message = "Hypothesis Analyst could not complete the requested analysis."
    state.workflow_notes.append("Logged a mismatch and exited without a Discovery draft.")
    return state


def route_after_assumptions(
    state: State,
    runtime: Runtime[ExecutorContext],
) -> Literal[
    "assumption_failed",
    "needs_empirical_metrics",
    "passed",
    "log_mismatch_and_exit",
]:
    if state.error_message is not None:
        return "log_mismatch_and_exit"
    if state.needs_data_exploration:
        return "needs_empirical_metrics"
    if state.assumption_failed:
        return "assumption_failed"
    return "passed"


def route_after_results(
    state: State,
    runtime: Runtime[ExecutorContext],
) -> Literal["draft_discovery_candidate", "log_mismatch_and_exit"]:
    if state.error_message is not None:
        return "log_mismatch_and_exit"
    if not state.evidence_drafts:
        return "log_mismatch_and_exit"
    return "draft_discovery_candidate"
"""LangGraph node functions for the Data Explorer workflow.

Nodes
-----
planning      - Translate task instruction into bounded AnalysisStep list.
execute       - Run each pending step via tools or sandboxed code; retry up to 3x.
check_result  - Evaluate completeness; route back to planning or emit Evidence/DataProfile.

Tool calls are placeholders: `_run_builtin_tool` and `_run_code_sandbox` return
stub outputs so the graph runs end-to-end without real dataset access.
"""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import uuid4

from langgraph.runtime import Runtime

from cognieda.schemas.artifacts import DataProfile, Evidence
from cognieda.schemas.common import EvidenceProvenance

from .context import Context
from .model import DataExplorerDecisionModel
from .types import (
    AnalysisStep,
    DEControlledError,
    DEErrorCode,
    EvaluationVerdict,
    EvaluationOutput,
    ExecutionType,
    PlanningOutput,
    State,
    StepResult,
    StepStatus,
)

_MAX_STEP_RETRIES = 3

# ---------------------------------------------------------------------------
# Placeholder tool executors
# ---------------------------------------------------------------------------


def _run_builtin_tool(
    tool_name: str,
    columns: list[str],
) -> dict[str, Any]:
    """Placeholder: returns a stub dict for the named builtin tool.

    Will be replaced by real deterministic tool dispatch in the next phase.
    """
    return {
        "tool": tool_name,
        "columns": columns,
        "result": "__placeholder__",
    }


def _run_code_sandbox(
    code: str,
    columns: list[str],
) -> dict[str, Any]:
    """Placeholder: returns a stub dict for sandboxed code execution.

    Will be replaced by real sandboxed Python/Pandas execution in the next phase.
    """
    return {
        "code_executed": True,
        "columns": columns,
        "result": "__placeholder__",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error(state: State, code: DEErrorCode, message: str) -> State:
    state.workflow_status = "failed"
    state.failure_reason = message
    state.emitted_evidence = None
    state.emitted_data_profile = None
    return state


def _execute_step(step: AnalysisStep) -> tuple[dict[str, Any], str | None]:
    """Dispatch one step to the appropriate placeholder executor.

    Returns (payload, error_message). error_message is None on success.
    """
    try:
        if step.execution_type is ExecutionType.BUILTIN_TOOL:
            if step.builtin_tool_name is None:
                return {}, "builtin_tool_name is required for BUILTIN_TOOL steps."
            payload = _run_builtin_tool(step.builtin_tool_name, step.target_columns)
        else:
            if step.generated_code is None:
                return {}, "generated_code is required for CODE_GENERATION steps."
            payload = _run_code_sandbox(step.generated_code, step.target_columns)
        return payload, None
    except Exception as exc:  # noqa: BLE001
        return {}, str(exc)


def _build_planning_prompt(state: State, context: Context) -> str:
    profile_json = (
        context.de_input.data_profile.model_dump_json()
        if context.de_input.data_profile is not None
        else "null"
    )
    parts = [
        f"Task instruction: {state.task_instruction}",
        f"Dataset path: {state.dataset_path}",
        f"DataProfile: {profile_json}",
    ]
    if state.revision_feedback:
        parts.append(f"Revision feedback from previous iteration: {state.revision_feedback}")
    if state.execution_results:
        succeeded = [r for r in state.execution_results if r.status is StepStatus.SUCCEEDED]
        if succeeded:
            parts.append(
                "Already-succeeded steps (do not repeat):\n"
                + json.dumps([r.step_id for r in succeeded])
            )
    return "\n\n".join(parts)


def _build_evaluation_prompt(state: State) -> str:
    results_json = json.dumps(
        [r.model_dump(mode="json") for r in state.execution_results],
        default=str,
    )
    return (
        f"Task instruction: {state.task_instruction}\n\n"
        f"Accumulated execution results:\n{results_json}"
    )


def _build_evidence(state: State) -> Evidence:
    """Construct an Evidence object from accumulated successful step results."""
    content: dict[str, Any] = {}
    variables_accessed: list[str] = []

    for result in state.execution_results:
        if result.status is StepStatus.SUCCEEDED:
            content[result.step_id] = result.output_payload
            variables_accessed.extend(result.variables_accessed)

    provenance = EvidenceProvenance(
        producer_role="data_explorer",
        work_reference=f"de:{uuid4()}",
        dataset_reference=state.dataset_path,
        data_profile_id=state.data_profile.data_profile_id,  # type: ignore[union-attr]
        tool_reference="cognieda.data_explorer.langgraph_agent:v1",
    )

    return Evidence(
        task_id=state.task_id,
        data_profile_id=state.data_profile.data_profile_id,  # type: ignore[union-attr]
        content=content,
        provenance=provenance,
    )


# ---------------------------------------------------------------------------
# Node 1: planning
# ---------------------------------------------------------------------------


async def planning(state: State, runtime: Runtime[Context]) -> State:
    """Translate task instruction into a bounded list of AnalysisStep objects.

    On the first iteration this produces the initial plan.
    On subsequent iterations it revises the plan based on revision_feedback
    provided by check_result.
    """
    if state.workflow_status in ("failed", "blocked", "succeeded"):
        return state

    model = cast(DataExplorerDecisionModel, runtime.context.de_model)
    prompt = _build_planning_prompt(state, runtime.context)

    try:
        output: PlanningOutput = await model.plan(prompt)
        state.plan = list(output.steps)
    except Exception as exc:  # noqa: BLE001
        return _error(
            state,
            DEErrorCode.PLANNING_FAILED,
            f"Data Explorer planning could not produce a valid plan: {exc}",
        )

    return state


# ---------------------------------------------------------------------------
# Node 2: execute
# ---------------------------------------------------------------------------


async def execute(state: State, runtime: Runtime[Context]) -> State:
    """Run every pending plan step; retry failed steps up to _MAX_STEP_RETRIES times.

    Each step outcome is appended to state.execution_results.
    Steps that exhaust all retries are recorded as FAILED but do not abort the
    remaining steps — check_result decides whether to route back to planning.
    """
    if state.workflow_status in ("failed", "blocked", "succeeded"):
        return state

    if not state.plan:
        return _error(
            state,
            DEErrorCode.EXECUTION_FAILED,
            "Execute node received an empty plan from planning.",
        )

    # Build a set of step_ids already in execution_results (from prior iterations)
    prior_ids = {r.step_id for r in state.execution_results}

    for step in state.plan:
        if step.step_id in prior_ids:
            # Skip steps that already have a recorded result
            continue

        retry_count = 0
        payload: dict[str, Any] = {}
        error_msg: str | None = None

        while retry_count <= _MAX_STEP_RETRIES:
            payload, error_msg = _execute_step(step)
            if error_msg is None:
                break
            retry_count += 1

        if error_msg is not None:
            # All retries exhausted
            state.execution_results.append(
                StepResult(
                    step_id=step.step_id,
                    status=StepStatus.FAILED,
                    error=error_msg,
                    retry_count=retry_count,
                )
            )
        else:
            state.execution_results.append(
                StepResult(
                    step_id=step.step_id,
                    status=StepStatus.SUCCEEDED,
                    output_payload=payload,
                    variables_accessed=list(step.target_columns),
                    retry_count=retry_count,
                )
            )

    return state


# ---------------------------------------------------------------------------
# Node 3: check_result
# ---------------------------------------------------------------------------


async def check_result(state: State, runtime: Runtime[Context]) -> State:
    """Evaluate execution completeness and either emit output or request revision.

    Routing decisions
    -----------------
    SATISFIED      -> construct Evidence or DataProfile; workflow_status = succeeded.
    NEEDS_REVISION -> increment iteration; set revision_feedback; return to planning.
    UNFEASIBLE     -> workflow_status = blocked.
    Budget exhaust -> workflow_status = failed.
    """
    if state.workflow_status in ("failed", "blocked", "succeeded"):
        return state

    model = cast(DataExplorerDecisionModel, runtime.context.de_model)
    prompt = _build_evaluation_prompt(state)

    try:
        evaluation: EvaluationOutput = await model.evaluate(prompt)
    except Exception as exc:  # noqa: BLE001
        return _error(
            state,
            DEErrorCode.EVALUATION_FAILED,
            f"Data Explorer evaluation agent failed: {exc}",
        )

    if evaluation.verdict is EvaluationVerdict.SATISFIED:
        _emit_output(state)
        return state

    if evaluation.verdict is EvaluationVerdict.UNFEASIBLE:
        state.workflow_status = "blocked"
        state.failure_reason = evaluation.revision_feedback or evaluation.summary
        return state

    # NEEDS_REVISION path
    state.iteration += 1
    if state.iteration >= state.max_iterations:
        return _error(
            state,
            DEErrorCode.MAX_ITERATIONS_EXCEEDED,
            (
                f"Data Explorer exhausted {state.max_iterations} planning iterations "
                "without satisfying the request. "
                f"Last feedback: {evaluation.revision_feedback or evaluation.summary}"
            ),
        )

    state.revision_feedback = evaluation.revision_feedback or evaluation.summary
    return state


def _emit_output(state: State) -> None:
    """Construct and store the admitted domain object on the state."""
    is_profiling_task = state.data_profile is None

    if is_profiling_task:
        # Profiling: DataProfile construction is a placeholder until the
        # deterministic profiling tool is wired in (next phase).
        # We mark blocked to avoid emitting an unverified DataProfile.
        state.workflow_status = "blocked"
        state.failure_reason = (
            "DataProfile construction from sandboxed output is deferred to the "
            "tool-implementation phase."
        )
        return

    try:
        evidence = _build_evidence(state)
        state.emitted_evidence = evidence
        state.workflow_status = "succeeded"
    except Exception as exc:  # noqa: BLE001
        state.workflow_status = "failed"
        state.failure_reason = f"Evidence construction failed: {exc}"


__all__ = ("check_result", "execute", "planning")

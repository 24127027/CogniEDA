"""LangGraph node functions for the Data Explorer workflow.

Nodes
-----
planning      - Translate task instruction into bounded AnalysisStep list.
execute       - Run each pending step via builtin tools or sandboxed code; retry up to 3x.
check_result  - Evaluate completeness; route back to planning or emit Evidence/DataProfile.

Builtin tool dispatch routes AnalysisStep definitions to the FunctionToolset
implementations in ``tools/``.  The execute node constructs bound toolsets
from the live DataFrame and calls the underlying Python functions by name.
"""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import uuid4

import pandas as pd
from langgraph.runtime import Runtime

from cognieda.schemas.artifacts import DataProfile, Evidence
from cognieda.schemas.common import EvidenceProvenance

from .dependencies import DEDependencies
from .tools import eda_toolset, profiling_toolset, sandbox_toolset

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
# Tool dispatch
# ---------------------------------------------------------------------------


def _extract_tool_function(
    tool_name: str,
    df: pd.DataFrame,
) -> Any | None:
    """Look up a tool function by name across profiling and EDA toolsets.

    Instantiates both toolsets bound to ``df``, then walks their registered
    tools to find a match on ``tool_name``.
    Returns the callable or None if not found.
    """
    for factory in (profiling_toolset, eda_toolset):
        ts = factory(df)
        
        # Pydantic AI versions vary: ts.tools might be a list of Tools or a dict of name -> Tool
        tools_coll = getattr(ts, "tools", None)
        if tools_coll is None:
            tools_coll = getattr(ts, "_tools", [])
            
        if isinstance(tools_coll, dict):
            # It's a dict, keys are names, values are Tool objects
            tool = tools_coll.get(tool_name)
            if tool is not None:
                return getattr(tool, "function", getattr(tool, "_function", getattr(tool, "func", None)))
        else:
            # It's a list or sequence
            for tool in tools_coll:
                if isinstance(tool, str):
                    # If the collection itself is just a list of strings, maybe ts behaves like a dict?
                    if tool == tool_name:
                        return getattr(ts, tool_name, None)
                else:
                    name = getattr(tool, "name", getattr(tool, "__name__", None))
                    if name == tool_name:
                        return getattr(tool, "function", getattr(tool, "_function", getattr(tool, "func", None)))
    return None


def _run_builtin_tool(
    tool_name: str,
    kwargs: dict[str, Any],
    df: pd.DataFrame,
) -> dict[str, Any]:
    """Dispatch a builtin tool call by name with the given keyword arguments.

    Constructs profiling_toolset and eda_toolset bound to ``df``, locates
    the tool function matching ``tool_name``, and invokes it.
    """
    func = _extract_tool_function(tool_name, df)
    if func is None:
        raise ValueError(
            f"Unknown builtin tool '{tool_name}'. "
            "Check the tool catalogue in tools/Built-in_tools.md."
        )
    result = func(**kwargs)
    if not isinstance(result, dict):
        result = {"value": result}
    return result


def _run_code_sandbox(
    code: str,
    target_columns: list[str],
    df: pd.DataFrame,
) -> dict[str, Any]:
    """Execute LLM-generated code via the sandbox toolset.

    Constructs sandbox_toolset bound to ``df`` and calls its ``execute_code``
    tool with the provided code and target columns.
    """
    ts = sandbox_toolset(df)
    # Extract the execute_code function from the sandbox toolset
    exec_func = None
    for tool in ts.tools:
        if tool.name == "execute_code":
            exec_func = tool.function
            break
    if exec_func is None:
        raise RuntimeError("sandbox_toolset missing execute_code tool.")
    return exec_func(code=code, target_columns=target_columns)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _error(state: State, code: DEErrorCode, message: str) -> State:
    state.workflow_status = "failed"
    state.failure_reason = message
    state.emitted_evidence = None
    state.emitted_data_profile = None
    return state


def _execute_step(
    step: AnalysisStep,
    df: pd.DataFrame,
) -> tuple[dict[str, Any], str | None]:
    """Dispatch one step to the appropriate tool executor.

    Returns (payload, error_message). error_message is None on success.
    """
    try:
        if step.execution_type is ExecutionType.BUILTIN_TOOL:
            if step.builtin_tool_name is None:
                return {}, "builtin_tool_name is required for BUILTIN_TOOL steps."
            payload = _run_builtin_tool(
                step.builtin_tool_name,
                step.builtin_tool_kwargs,
                df,
            )
        else:
            if step.generated_code is None:
                return {}, "generated_code is required for CODE_GENERATION steps."
            payload = _run_code_sandbox(
                step.generated_code,
                step.target_columns,
                df,
            )
        return payload, None
    except Exception as exc:  # noqa: BLE001
        return {}, str(exc)


def _load_df(context: Context) -> pd.DataFrame:
    """Return an in-memory DataFrame from context.

    During the MVP phase the DataFrame is expected to be pre-loaded by the
    caller and attached to ``context.de_input``.  When it is absent (e.g. in
    tests or stub runs) an empty DataFrame is returned so toolset factories
    still succeed.
    """
    raw = getattr(context.de_input, "dataframe", None)
    if isinstance(raw, pd.DataFrame):
        return raw.copy(deep=True)
    return pd.DataFrame()


def _build_planning_prompt(state: State, context: Context) -> str:
    is_profiling_task = context.de_input.data_profile is None

    # --- Boundary enforcement header (applies to all task paths) ---
    # The DE is a mechanical data observer only. It extracts facts from data
    # and profiles schemas.  It never draws scientific conclusions, performs
    # statistical correlation between non-numeric/string columns, interprets
    # patterns, or answers questions about dataset meaning.
    _BOUNDARY = (
        "ROLE BOUNDARY: You are a mechanical data observer. "
        "You may ONLY produce AnalysisStep entries that extract raw data facts "
        "(e.g. row counts, column names, missing value counts, value distributions, "
        "numeric statistics, duplicate detection). "
        "You must NOT attempt: scientific interpretation, statistical correlation of "
        "non-numeric columns (e.g. string IDs or emails), natural-language summaries "
        "of relationships, or any reasoning that goes beyond direct data extraction. "
        "If the task instruction asks for something outside these bounds, return a "
        "single-step plan with execution_type=BUILTIN_TOOL, builtin_tool_name='inspect_schema', "
        "and set the step description to 'UNFEASIBLE: <reason>'. "
        "The evaluator will detect this marker and reject the request cleanly."
    )

    if is_profiling_task:
        parts = [
            _BOUNDARY,
            "CRITICAL: The context lacks a DataProfile.",
            "You MUST emit a plan with a single step that invokes the 'profile_dataset' builtin tool.",
            "DO NOT attempt to perform the user's task instruction yet. Your only goal right now is to generate the profile.",
        ]
    else:
        profile_json = context.de_input.data_profile.model_dump_json()
        parts = [
            _BOUNDARY,
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
    succeeded_count = sum(
        1 for r in state.execution_results if r.status is StepStatus.SUCCEEDED
    )
    return (
        f"Task instruction: {state.task_instruction}\n\n"
        f"Accumulated execution results:\n{results_json}\n\n"
        f"Successful steps: {succeeded_count}\n\n"
        "EVALUATION RULES:\n"
        "1. You must return SATISFIED only if at least one step SUCCEEDED and its "
        "output_payload contains meaningful data that answers or materially advances "
        "the task instruction.\n"
        "2. If zero steps succeeded, you MUST return NEEDS_REVISION or UNFEASIBLE "
        "(never SATISFIED). An empty result cannot satisfy a task.\n"
        "3. If any step description starts with 'UNFEASIBLE:', return UNFEASIBLE "
        "and set revision_feedback to that description.\n"
        "4. If the task requests scientifically invalid operations (e.g. correlation "
        "between non-numeric/string columns), return UNFEASIBLE.\n"
        "5. Return NEEDS_REVISION only if the data gathered is incomplete but the "
        "task is still technically achievable with a revised plan."
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

    df = _load_df(runtime.context)

    # Build research context for the planning agent.
    # Tools that use @toolset.tool can access DataProfile and Objective
    # via RunContext[DEDependencies] to validate column names before attempting ops.
    deps = DEDependencies(
        data_profile=runtime.context.de_input.data_profile,
        objective=getattr(runtime.context.de_input, "objective", None),
    )

    try:
        output: PlanningOutput = await model.plan(prompt, df, deps=deps)
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

    # Load the DataFrame once for the entire execution turn.
    df = _load_df(runtime.context)

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
            payload, error_msg = _execute_step(step, df)
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
    df = _load_df(runtime.context)

    # Build research context for the evaluation agent (same as planning).
    deps = DEDependencies(
        data_profile=runtime.context.de_input.data_profile,
        objective=getattr(runtime.context.de_input, "objective", None),
    )

    try:
        evaluation: EvaluationOutput = await model.evaluate(prompt, df, deps=deps)
    except Exception as exc:  # noqa: BLE001
        return _error(
            state,
            DEErrorCode.EVALUATION_FAILED,
            f"Data Explorer evaluation agent failed: {exc}",
        )

    if evaluation.verdict is EvaluationVerdict.SATISFIED:
        # Hard guardrail (Priority 2.1): the LLM may falsely report SATISFIED
        # even when all tool executions failed (output_payload is empty for every
        # step).  Trusting that verdict leads to Pydantic crashing downstream
        # when Evidence.content is validated as empty.  We override here.
        has_successful_payload = any(
            r.status is StepStatus.SUCCEEDED and r.output_payload
            for r in state.execution_results
        )
        if not has_successful_payload:
            # Override to NEEDS_REVISION unless we are at the iteration budget;
            # in that case treat as UNFEASIBLE to avoid infinite loops.
            if state.iteration >= state.max_iterations - 1:
                state.workflow_status = "blocked"
                state.failure_reason = (
                    "All execution steps failed to produce output. "
                    "The request cannot be fulfilled with the available data "
                    "and tools. Original evaluation summary: "
                    + evaluation.summary
                )
                return state
            # Force a revision with explanation.
            state.iteration += 1
            state.revision_feedback = (
                "GUARDRAIL OVERRIDE: The previous plan produced zero successful "
                "output payloads. Revise the plan to use only supported builtin "
                "tools or valid code on numeric/string columns that exist in the "
                "DataProfile. If the task is not achievable with these tools, "
                "return a single step with description starting 'UNFEASIBLE: <reason>'."
            )
            return state
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
        # Look for a profile_dataset result in execution_results.
        for result in state.execution_results:
            if (
                result.status is StepStatus.SUCCEEDED
                and result.output_payload
                and "columns" in result.output_payload
                and "row_count" in result.output_payload
            ):
                try:
                    profile = DataProfile.model_validate(result.output_payload)
                    state.emitted_data_profile = profile
                    state.workflow_status = "succeeded"
                    return
                except Exception:  # noqa: BLE001
                    pass  # Not a valid DataProfile shape; continue searching.

        # No profile_dataset result found — fall back to blocked.
        state.workflow_status = "blocked"
        state.failure_reason = (
            "Profiling task completed but no valid DataProfile could be "
            "constructed from execution results."
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

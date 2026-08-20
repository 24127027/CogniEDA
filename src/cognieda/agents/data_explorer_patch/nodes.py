"""Node implementations for DataExplorer patch workflow."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from langgraph.graph import END
from langgraph.runtime import Runtime
from pydantic_ai.messages import ToolCallPart, ToolReturnPart

from cognieda.schemas.artifacts import DataProfile, Evidence
from cognieda.schemas.common import EvidenceProvenance

from .context import Context
from .instructions import (
    CHECK_RESULT_PROMPT,
    DATA_EXPLORER_BASE_INSTRUCTION,
    EXECUTE_PROMPT,
    PLANNING_PROMPT_TEMPLATE,
    PLANNING_REVISION_PROMPT_TEMPLATE,
)
from .state import State


def _resolve_data_profile_id(
    runtime: Runtime[Context],
    artifacts: list[DataProfile | Evidence],
) -> UUID | None:
    """Resolve authoritative data_profile_id without fabricating identifiers."""
    deps = getattr(runtime.context, "deps", None)
    if deps and getattr(deps, "data_profile_id", None) is not None:
        return deps.data_profile_id

    for art in artifacts:
        if isinstance(art, DataProfile):
            return art.data_profile_id

    ctx = getattr(runtime.context, "context", None)
    if ctx and hasattr(ctx, "content") and ctx.content:
        for item in ctx.content:
            if isinstance(item, DataProfile):
                return item.data_profile_id

    return None


def _extract_tool_executions(messages: list[Any]) -> list[tuple[str, dict[str, Any], Any]]:
    """Extract tool call arguments and returns from message history."""
    calls: dict[str, tuple[str, dict[str, Any]]] = {}
    executions: list[tuple[str, dict[str, Any], Any]] = []

    for msg in messages:
        parts = msg.parts if hasattr(msg, "parts") else [msg]
        for part in parts:
            if isinstance(part, ToolCallPart):
                args = part.args if isinstance(part.args, dict) else {}
                calls[part.tool_call_id] = (part.tool_name, args)
            elif isinstance(part, ToolReturnPart):
                call_info = calls.get(part.tool_call_id, (part.tool_name, {}))
                executions.append((part.tool_name, call_info[1], part.content))
    return executions


async def planning(state: State, runtime: Runtime[Context]) -> State:
    """Planning node of the DataExplorer agent's internal workflow."""
    iterations = state.get("iterations", 0) + 1
    state["iterations"] = iterations

    # Preserve existing valid artifacts across revision iterations
    artifacts = list(state.get("artifacts") or [])

    feedback = state.get("feedback")
    if feedback and not feedback.upper().startswith("YES"):
        if artifacts:
            obs_lines = []
            for art in artifacts:
                if isinstance(art, DataProfile):
                    obs_lines.append(
                        f"- DataProfile (rows={art.row_count}, columns={art.column_count})"
                    )
                elif isinstance(art, Evidence):
                    tool_name = (
                        art.provenance.tool_reference
                        or art.provenance.work_reference
                    )
                    obs_lines.append(
                        f"- Evidence from '{tool_name}' on columns {art.artifact_refs}"
                    )
            obs_str = "\n".join(obs_lines)
        else:
            obs_str = "None yet."

        prompt = PLANNING_REVISION_PROMPT_TEMPLATE.format(
            feedback=feedback,
            existing_observations=obs_str,
        )
    else:
        context_obj = getattr(runtime.context, "context", None)
        if context_obj is not None and hasattr(context_obj, "model_dump_json"):
            context_json = context_obj.model_dump_json()
        else:
            context_json = "{}"

        prompt = PLANNING_PROMPT_TEMPLATE.format(
            context_json=context_json,
            task_input=state.get("input", ""),
        )

    result = await runtime.context.agent.run(
        prompt,
        deps=runtime.context.deps,
        message_history=state.get("messages", []),
        instructions=DATA_EXPLORER_BASE_INSTRUCTION,
    )

    return {
        **state,
        "iterations": iterations,
        "artifacts": artifacts,
        "messages": result.all_messages(),
    }


async def execute(state: State, runtime: Runtime[Context]) -> State:
    """Execute node of the DataExplorer agent's internal workflow."""
    result = await runtime.context.agent.run(
        EXECUTE_PROMPT,
        deps=runtime.context.deps,
        message_history=state.get("messages", []),
        instructions=DATA_EXPLORER_BASE_INSTRUCTION,
    )

    artifacts = list(state.get("artifacts") or [])
    new_messages = result.new_messages() if hasattr(result, "new_messages") else []
    executions = _extract_tool_executions(new_messages)

    for tool_name, tool_args, tool_content in executions:
        if isinstance(tool_content, DataProfile):
            # Authoritative DataProfile without ungrounded LLM enrichment
            artifacts.append(tool_content)
        elif isinstance(tool_content, dict):
            # Exclude execution errors from empirical evidence
            if tool_content.get("error") is not None:
                continue

            profile_id = _resolve_data_profile_id(runtime, artifacts)
            if profile_id is None:
                # Do NOT fabricate random UUIDs. Fail-closed without valid profile provenance.
                continue

            artifact_refs: list[str] = []
            for key in ("column", "group_by", "value_column"):
                val = tool_args.get(key)
                if isinstance(val, str) and val:
                    artifact_refs.append(val)
            if "columns" in tool_args and isinstance(tool_args["columns"], (list, tuple)):
                for col in tool_args["columns"]:
                    if isinstance(col, str) and col:
                        artifact_refs.append(col)

            evidence = Evidence(
                data_profile_id=profile_id,
                content=tool_content,
                artifact_refs=tuple(artifact_refs),
                provenance=EvidenceProvenance(
                    producer_role="data_explorer",
                    work_reference=tool_name,
                    dataset_reference="active_dataframe",
                    data_profile_id=profile_id,
                    tool_reference=tool_name,
                    code_reference=(
                        tool_args.get("code")
                        if tool_name == "execute_code"
                        and isinstance(tool_args.get("code"), str)
                        else None
                    ),
                ),
            )
            artifacts.append(evidence)

    return {
        **state,
        "artifacts": artifacts,
        "messages": result.all_messages(),
    }


async def check_result(state: State, runtime: Runtime[Context]) -> State:
    """Check result node of the DataExplorer agent's internal workflow."""
    result = await runtime.context.agent.run(
        CHECK_RESULT_PROMPT,
        deps=runtime.context.deps,
        message_history=state.get("messages", []),
        instructions=DATA_EXPLORER_BASE_INSTRUCTION,
    )

    output = getattr(result, "output", getattr(result, "data", ""))
    feedback = str(output).strip()

    return {
        **state,
        "messages": result.all_messages(),
        "feedback": feedback,
    }


def _route_after_check_result(state: State) -> str:
    """Determine the next node after check_result based on the state."""
    feedback = state.get("feedback", "")
    if feedback.upper().startswith("YES"):
        return END
    iterations = state.get("iterations", 0)
    if iterations < 3:
        return "planning"
    return END
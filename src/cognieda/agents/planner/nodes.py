from __future__ import annotations

from typing import Any, Literal, cast

from langgraph.runtime import Runtime
from pydantic import TypeAdapter
from pydantic_ai import Agent

from .context import PlannerGraphContext
from .contracts import (
    AuthoritativeAnswerRequest,
    DirectResponse,
    PlannerAnswerContext,
    PlannerCognitiveResult,
    PlannerControlledError,
    PlannerErrorCode,
)
from .dependencies import PlannerDeps
from .state import PlannerState

_RESULT_ADAPTER: TypeAdapter[PlannerCognitiveResult] = TypeAdapter(
    PlannerCognitiveResult
)


def _fail(
    state: PlannerState,
    code: PlannerErrorCode,
    message: str,
) -> PlannerState:
    state.error = PlannerControlledError(code=code, message=message)
    state.result = DirectResponse(text=message)
    return state


async def run_planner(
    state: PlannerState,
    runtime: Runtime[PlannerGraphContext],
) -> PlannerState:
    """Run one complete Planner reasoning/tool-use turn."""

    try:
        agent = cast(Agent[PlannerDeps, object], runtime.context.agent)
        prompt = (
            f"Current Human request:\n{state.request}\n\n"
            "Authorized Planner research context:\n"
            f"{runtime.context.planner_context.model_dump_json()}"
        )
        result = await agent.run(
            prompt,
            output_type=cast(Any, PlannerCognitiveResult),
            message_history=runtime.context.conversation_history.model_messages(),
            instructions=runtime.context.planner_instructions,
            deps=runtime.context.deps,
        )
        state.result = _RESULT_ADAPTER.validate_python(result.output)
        state.new_messages = (*state.new_messages, *result.new_messages())
    except Exception as exc:
        _fail(
            state,
            PlannerErrorCode.INVALID_MODEL_RESULT,
            f"Planner could not produce a valid typed result: {exc}",
        )
    return state


def route_after_planner(
    state: PlannerState,
) -> Literal["compose_authoritative_answer", "__end__"]:
    """Enter the protected answer boundary only when explicitly requested."""

    if isinstance(state.result, AuthoritativeAnswerRequest):
        return "compose_authoritative_answer"
    return "__end__"


async def compose_authoritative_answer(
    state: PlannerState,
    runtime: Runtime[PlannerGraphContext],
) -> PlannerState:
    """Draft prose from Evidence/Discovery support isolated from planning context."""

    planner_context = runtime.context.planner_context
    if not planner_context.evidences and not planner_context.discoveries:
        return _fail(
            state,
            PlannerErrorCode.NO_AUTHORITATIVE_SUPPORT,
            "No admitted Evidence or governed Discovery is available to support an answer.",
        )

    try:
        agent = cast(Agent[PlannerDeps, object], runtime.context.agent)
        answer_context = PlannerAnswerContext(
            request=state.request,
            objective=planner_context.objective,
            data_profile=planner_context.data_profile,
            evidences=planner_context.evidences,
            discoveries=planner_context.discoveries,
        )
        result = await agent.run(
            f"Authorized answer context:\n{answer_context.model_dump_json()}",
            output_type=DirectResponse,
            instructions=runtime.context.answer_instructions,
            deps=runtime.context.deps,
        )
        state.result = DirectResponse.model_validate(result.output)
        state.new_messages = (*state.new_messages, *result.new_messages())
    except Exception as exc:
        _fail(
            state,
            PlannerErrorCode.RESPONSE_FAILED,
            f"Planner could not compose an authoritative-context response: {exc}",
        )
    return state

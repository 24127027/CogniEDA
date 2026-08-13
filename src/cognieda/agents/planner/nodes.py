from __future__ import annotations

from typing import Any, cast

from langgraph.runtime import Runtime
from pydantic import TypeAdapter
from pydantic_ai import Agent

from cognieda.schemas.artifacts import Objective
from cognieda.schemas.enums import AssumptionTestability

from .context import PlannerGraphContext
from .contracts import (
    AnswerFromContextDecision,
    AssumptionAssessment,
    AssumptionAssessmentDecision,
    PlannerAnswerContext,
    PlannerControlledError,
    PlannerDecision,
    PlannerErrorCode,
    PlannerResponseDraft,
    SetOrRefineObjectiveDecision,
    StateSummaryDecision,
    UnsupportedDecision,
)
from .state import PlannerState

_DECISION_ADAPTER: TypeAdapter[PlannerDecision] = TypeAdapter(PlannerDecision)


def _error(code: PlannerErrorCode, message: str) -> PlannerControlledError:
    return PlannerControlledError(code=code, message=message)


def _explicit_decision(
    request: str,
) -> tuple[PlannerDecision | None, PlannerControlledError | None] | None:
    stripped = request.strip()
    if not stripped.startswith("/"):
        return None

    command, _, payload = stripped.partition(" ")
    command = command.casefold()
    payload = payload.strip()

    if command == "/summary":
        if payload:
            return None, _error(
                PlannerErrorCode.INVALID_COMMAND,
                "The /summary command does not accept additional text.",
            )
        return StateSummaryDecision(), None

    if command in {
        "/objective",
        "/assumption",
        "/answer",
        "/profile",
        "/analyze",
        "/transform",
    }:
        if not payload:
            return None, _error(
                PlannerErrorCode.INVALID_COMMAND,
                f"The {command} command requires request text.",
            )
        if command == "/objective":
            return SetOrRefineObjectiveDecision(objective=Objective(text=payload)), None
        if command == "/assumption":
            return (
                AssumptionAssessmentDecision(
                    assessment=AssumptionAssessment(
                        source_text=payload,
                        testability=AssumptionTestability.UNTESTABLE_IN_PROJECT,
                    )
                ),
                None,
            )
        if command == "/answer":
            return AnswerFromContextDecision(), None
        return (
            UnsupportedDecision(
                message=(
                    f"{command} DATA work is deferred until canonical plan approval and "
                    "semantic specialist-tool admission are implemented."
                )
            ),
            None,
        )

    return None, _error(
        PlannerErrorCode.INVALID_COMMAND,
        (
            f"Unknown Planner command {command}. Supported commands are /objective, "
            "/assumption, /profile, /analyze, /transform, /answer, and /summary."
        ),
    )


async def understand_request(
    state: PlannerState,
    runtime: Runtime[PlannerGraphContext],
) -> PlannerState:
    """Produce one typed intent from the current request and authorized context."""

    explicit = _explicit_decision(state.request)
    if explicit is not None:
        state.decision, state.error = explicit
        return state

    try:
        agent = cast(Agent[object, object], runtime.context.agent)
        prompt = (
            f"Current Human request:\n{state.request}\n\n"
            "Authorized Planner research context:\n"
            f"{runtime.context.planner_context.model_dump_json()}"
        )
        result = await agent.run(
            prompt,
            output_type=cast(Any, PlannerDecision),
            message_history=runtime.context.conversation_history.model_messages(),
            instructions=runtime.context.decide_instructions,
            deps=runtime.context.deps,
        )
        state.decision = _DECISION_ADAPTER.validate_python(result.output)
        state.new_messages = (*state.new_messages, *result.new_messages())
    except Exception as exc:
        state.error = _error(
            PlannerErrorCode.INVALID_MODEL_DECISION,
            f"Planner could not produce a valid typed decision: {exc}",
        )
    return state


async def prepare_results(
    state: PlannerState,
    runtime: Runtime[PlannerGraphContext],
) -> PlannerState:
    """Expose only application-authorized proposals and assessments."""

    del runtime
    if state.error is not None or state.decision is None:
        return state

    decision = state.decision
    if isinstance(decision, SetOrRefineObjectiveDecision):
        state.objective_proposal = decision.objective
    elif isinstance(decision, AssumptionAssessmentDecision):
        state.assumption_assessment = decision.assessment
    elif isinstance(decision, UnsupportedDecision):
        state.error = _error(PlannerErrorCode.UNSUPPORTED_ACTION, decision.message)
    return state


async def compose_response(
    state: PlannerState,
    runtime: Runtime[PlannerGraphContext],
) -> PlannerState:
    """Present state without upgrading conversation or planning context to support."""

    if state.error is not None:
        state.response = state.error.message
        return state

    decision = state.decision
    if decision is None:
        state.error = _error(
            PlannerErrorCode.MODEL_UNAVAILABLE,
            "Planner request understanding is unavailable.",
        )
        state.response = state.error.message
        return state

    planner_context = runtime.context.planner_context
    if isinstance(decision, AnswerFromContextDecision):
        if not planner_context.evidences and not planner_context.discoveries:
            state.error = _error(
                PlannerErrorCode.NO_AUTHORITATIVE_SUPPORT,
                "No admitted Evidence or governed Discovery is available to support an answer.",
            )
            state.response = state.error.message
            return state
        try:
            agent = cast(Agent[object, object], runtime.context.agent)
            answer_context = PlannerAnswerContext(
                request=state.request,
                objective=planner_context.objective,
                data_profile=planner_context.data_profile,
                evidences=planner_context.evidences,
                discoveries=planner_context.discoveries,
            )
            result = await agent.run(
                f"Authorized answer context:\n{answer_context.model_dump_json()}",
                output_type=PlannerResponseDraft,
                instructions=runtime.context.answer_instructions,
                deps=runtime.context.deps,
            )
            response = PlannerResponseDraft.model_validate(result.output)
            state.response = response.text
            state.new_messages = (*state.new_messages, *result.new_messages())
        except Exception as exc:
            state.error = _error(
                PlannerErrorCode.RESPONSE_FAILED,
                f"Planner could not compose an authoritative-context response: {exc}",
            )
            state.response = state.error.message
        return state

    if isinstance(decision, StateSummaryDecision):
        objective_text = (
            planner_context.objective.text
            if planner_context.objective is not None
            else "not established"
        )
        state.response = (
            f"Active Objective: {objective_text}. "
            f"Planning Assumptions (not support): {len(planner_context.assumptions)}. "
            f"Tasks: {len(planner_context.tasks)}. "
            f"Admitted Evidence items: {len(planner_context.evidences)}. "
            f"Governed Discoveries: {len(planner_context.discoveries)}."
        )
    elif isinstance(decision, SetOrRefineObjectiveDecision):
        state.response = f"Objective proposed: {decision.objective.text}"
    elif isinstance(decision, AssumptionAssessmentDecision):
        if (
            decision.assessment.testability
            is AssumptionTestability.UNTESTABLE_IN_PROJECT
        ):
            state.response = (
                f"Planning Assumption accepted from exact Human text: "
                f"{decision.assessment.source_text} It is not empirical support."
            )
        else:
            state.response = (
                "The statement is reasonably testable and was not admitted as an "
                "Assumption."
            )
    else:
        state.response = decision.message
    return state

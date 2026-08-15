"""In-process LangGraph lifecycle for the Human-facing Planner."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from typing import Any, Literal, TypedDict, cast
from uuid import UUID, uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command, StateSnapshot, interrupt
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai.messages import ModelMessage

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.types import (
    PlannerControlledError,
    PlannerErrorCode,
    PlannerResult,
)
from cognieda.application.services import PlanAdmissionService
from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan import Plan

from .planner_context import PlannerContextProvider

_ACTIVE_PLAN_EXECUTION_DEFERRED = (
    "The active Plan is ready to continue, but Plan execution is not implemented "
    "in this runtime phase."
)
_CANDIDATE_ADMITTED = "The proposed Plan was admitted and activated."
_CANDIDATE_DISCARDED = "The proposed Plan was discarded."
_END_NODE: Literal["__end__"] = "__end__"


class PlannerTurnOutcome(BaseModel):
    """Typed presentation facts produced by one completed or interrupted graph turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_plan: Plan | None = None
    candidate_tasks: tuple[Task, ...] = ()
    response: str | None = Field(default=None, min_length=1)
    human_input_request: str | None = Field(default=None, min_length=1)
    candidate_admitted: bool = False
    candidate_discarded: bool = False
    active_plan_continuation_deferred: bool = False
    awaiting_human: bool = False
    error: PlannerControlledError | None = None

    @model_validator(mode="after")
    def _validate_coherence(self) -> PlannerTurnOutcome:
        if self.candidate_tasks and self.candidate_plan is None:
            raise ValueError("Outcome candidate Tasks require a candidate Plan.")
        if self.candidate_plan is not None:
            self.candidate_plan.validate_tasks(self.candidate_tasks)
        if not any(
            (
                self.candidate_plan is not None,
                self.response is not None,
                self.human_input_request is not None,
                self.candidate_admitted,
                self.candidate_discarded,
                self.active_plan_continuation_deferred,
                self.error is not None,
            )
        ):
            raise ValueError("PlannerTurnOutcome requires a visible or controlled result.")
        return self


class PlannerGraphState(TypedDict):
    """Checkpointed Planner lifecycle state; never authoritative research state."""

    latest_human_input: str | None
    candidate_plan: Plan | None
    candidate_tasks: tuple[Task, ...]
    messages: tuple[ModelMessage, ...]
    result: PlannerResult | None
    error: PlannerControlledError | None
    turn_outcome: PlannerTurnOutcome | None


@dataclass(frozen=True)
class PlannerRuntimeContext:
    """Stable invocation dependencies supplied through LangGraph runtime context."""

    planner: Planner
    planner_context_provider: PlannerContextProvider
    plan_admission: PlanAdmissionService


def _validate_candidate_state(state: PlannerGraphState) -> None:
    plan = state["candidate_plan"]
    tasks = state["candidate_tasks"]
    if plan is None:
        if tasks:
            raise ValueError("Candidate Tasks require a retained candidate Plan.")
        return
    plan.validate_tasks(tasks)


def _controlled_error(
    code: PlannerErrorCode,
    message: str,
) -> PlannerControlledError:
    return PlannerControlledError(code=code, message=message)


async def _plan_or_answer(
    state: PlannerGraphState,
    runtime: Runtime[PlannerRuntimeContext],
) -> Command[Literal["await_human", "admit_candidate", "__end__"]]:
    _validate_candidate_state(state)
    request = state["latest_human_input"]
    if request is None or not request.strip():
        error = _controlled_error(
            PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            "Planner lifecycle requires a non-empty Human request.",
        )
        return Command(
            update={
                "result": None,
                "error": error,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )

    try:
        planner_context = runtime.context.planner_context_provider.materialize()
    except Exception:
        error = _controlled_error(
            PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            "Planner authoritative context could not be materialized.",
        )
        return Command(
            update={
                "result": None,
                "error": error,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )

    output = await runtime.context.planner.run(
        request,
        context=planner_context,
        candidate_plan=state["candidate_plan"],
        candidate_tasks=state["candidate_tasks"],
        message_history=list(state["messages"]),
    )
    messages = (*state["messages"], *output.messages)
    result = output.result
    base_update: dict[str, object] = {
        "messages": messages,
        "result": result,
        "error": output.error,
    }

    if output.error is not None:
        outcome = PlannerTurnOutcome(response=result.response, error=output.error)
        return Command(update={**base_update, "turn_outcome": outcome}, goto=_END_NODE)

    try:
        if result.plan is not None:
            result.plan.validate_tasks(result.tasks)
        if result.discard_candidate and state["candidate_plan"] is None:
            raise ValueError("discard_candidate requires a retained candidate.")
        if (
            result.continue_execution
            and state["candidate_plan"] is None
            and planner_context.active_plan is None
        ):
            raise ValueError("continue_execution requires a retained or active Plan.")
    except ValueError:
        error = _controlled_error(
            PlannerErrorCode.INVALID_LIFECYCLE_STATE,
            "Planner produced a result that is invalid for the retained lifecycle state.",
        )
        return Command(
            update={
                **base_update,
                "error": error,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )

    if result.plan is not None:
        outcome = PlannerTurnOutcome(
            candidate_plan=result.plan,
            candidate_tasks=result.tasks,
            response=result.response,
            human_input_request=result.human_input_request,
            awaiting_human=True,
        )
        return Command(
            update={
                **base_update,
                "candidate_plan": result.plan,
                "candidate_tasks": result.tasks,
                "turn_outcome": outcome,
            },
            goto="await_human",
        )

    if result.continue_execution:
        if state["candidate_plan"] is not None:
            return Command(update=base_update, goto="admit_candidate")
        outcome = PlannerTurnOutcome(
            response=_ACTIVE_PLAN_EXECUTION_DEFERRED,
            active_plan_continuation_deferred=True,
        )
        return Command(update={**base_update, "turn_outcome": outcome}, goto=_END_NODE)

    if result.discard_candidate:
        outcome = PlannerTurnOutcome(
            response=result.response or _CANDIDATE_DISCARDED,
            candidate_discarded=True,
        )
        return Command(
            update={
                **base_update,
                "candidate_plan": None,
                "candidate_tasks": (),
                "turn_outcome": outcome,
            },
            goto=_END_NODE,
        )

    awaiting_human = (
        result.human_input_request is not None or state["candidate_plan"] is not None
    )
    outcome = PlannerTurnOutcome(
        response=result.response,
        human_input_request=result.human_input_request,
        awaiting_human=awaiting_human,
    )
    return Command(
        update={**base_update, "turn_outcome": outcome},
        goto="await_human" if awaiting_human else _END_NODE,
    )


def _interrupt_reason(outcome: PlannerTurnOutcome) -> str:
    if outcome.human_input_request is not None:
        return "human_clarification"
    if outcome.candidate_plan is not None:
        return "candidate_review"
    return "candidate_followup"


def _await_human(
    state: PlannerGraphState,
) -> Command[Literal["plan_or_answer", "__end__"]]:
    outcome = state["turn_outcome"]
    if outcome is None:
        raise ValueError("Human wait requires a typed Planner turn outcome.")

    answer = interrupt({"reason": _interrupt_reason(outcome)})
    if not isinstance(answer, str) or not answer.strip():
        error = _controlled_error(
            PlannerErrorCode.INVALID_REQUEST,
            "Planner requests cannot be empty.",
        )
        return Command(
            update={
                "latest_human_input": None,
                "result": None,
                "error": error,
                "turn_outcome": PlannerTurnOutcome(error=error),
            },
            goto=_END_NODE,
        )
    return Command(
        update={
            "latest_human_input": answer,
            "result": None,
            "error": None,
            "turn_outcome": None,
        },
        goto="plan_or_answer",
    )


def _admit_candidate(
    state: PlannerGraphState,
    runtime: Runtime[PlannerRuntimeContext],
) -> dict[str, object]:
    _validate_candidate_state(state)
    plan = state["candidate_plan"]
    if plan is None:
        raise ValueError("Candidate admission requires a retained candidate Plan.")
    try:
        runtime.context.plan_admission.admit(
            plan,
            tasks=state["candidate_tasks"],
        )
    except Exception:
        error = _controlled_error(
            PlannerErrorCode.PLAN_ADMISSION_FAILED,
            "The proposed Plan could not be admitted; the candidate remains available.",
        )
        return {
            "error": error,
            "turn_outcome": PlannerTurnOutcome(error=error),
        }
    return {
        "candidate_plan": None,
        "candidate_tasks": (),
        "error": None,
        "turn_outcome": PlannerTurnOutcome(
            response=_CANDIDATE_ADMITTED,
            candidate_admitted=True,
        ),
    }


def _build_graph(
    checkpointer: BaseCheckpointSaver[Any],
) -> CompiledStateGraph[
    PlannerGraphState,
    PlannerRuntimeContext,
    PlannerGraphState,
    PlannerGraphState,
]:
    builder = StateGraph(PlannerGraphState, context_schema=PlannerRuntimeContext)
    builder.add_node("plan_or_answer", _plan_or_answer)
    builder.add_node("await_human", _await_human)
    builder.add_node("admit_candidate", _admit_candidate)
    builder.add_edge(START, "plan_or_answer")
    builder.add_edge("admit_candidate", END)
    return builder.compile(checkpointer=checkpointer)


def _empty_state(latest_human_input: str | None = None) -> PlannerGraphState:
    return PlannerGraphState(
        latest_human_input=latest_human_input,
        candidate_plan=None,
        candidate_tasks=(),
        messages=(),
        result=None,
        error=None,
        turn_outcome=None,
    )


def _state_from_snapshot(
    snapshot: StateSnapshot,
    *,
    latest_human_input: str | None = None,
) -> PlannerGraphState:
    if not snapshot.values:
        return _empty_state(latest_human_input)
    prior = cast(PlannerGraphState, snapshot.values)
    state = PlannerGraphState(
        latest_human_input=latest_human_input,
        candidate_plan=prior["candidate_plan"],
        candidate_tasks=tuple(prior["candidate_tasks"]),
        messages=tuple(prior["messages"]),
        result=prior["result"],
        error=prior["error"],
        turn_outcome=prior["turn_outcome"],
    )
    _validate_candidate_state(state)
    return state


def _is_interrupted(snapshot: StateSnapshot) -> bool:
    return any(task.interrupts for task in snapshot.tasks)


class _InProcessSerializer(SerializerProtocol):
    """Round-trip trusted in-memory typed state without weakening model validation."""

    def dumps_typed(self, obj: Any) -> tuple[str, bytes]:
        return "pickle", pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def loads_typed(self, data: tuple[str, bytes]) -> Any:
        kind, payload = data
        if kind != "pickle":
            raise ValueError("In-process Planner checkpoint has an unknown payload type.")
        return pickle.loads(payload)


class PlannerRuntime:
    """Own one in-process Planner graph thread and its lifecycle checkpoint state."""

    def __init__(
        self,
        *,
        runtime_context: PlannerRuntimeContext,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        thread_id: UUID | None = None,
    ) -> None:
        self.runtime_context = runtime_context
        self.checkpointer = checkpointer or InMemorySaver(serde=_InProcessSerializer())
        self.thread_id = thread_id or uuid4()
        self._config: RunnableConfig = {
            "configurable": {"thread_id": str(self.thread_id)}
        }
        self._graph = _build_graph(self.checkpointer)

    async def handle_message(self, message: str) -> PlannerTurnOutcome:
        snapshot = await self._graph.aget_state(self._config)
        if _is_interrupted(snapshot):
            graph_input: PlannerGraphState | Command[Any] = Command(resume=message)
        else:
            graph_input = _state_from_snapshot(
                snapshot,
                latest_human_input=message,
            )
            graph_input["result"] = None
            graph_input["error"] = None
            graph_input["turn_outcome"] = None

        await self._graph.ainvoke(
            graph_input,
            config=self._config,
            context=self.runtime_context,
        )
        current = await self._graph.aget_state(self._config)
        state = _state_from_snapshot(current)
        outcome = state["turn_outcome"]
        if outcome is None:
            raise RuntimeError("Planner graph completed without a typed turn outcome.")
        return outcome

    async def get_state(self) -> PlannerGraphState:
        """Inspect this runtime thread's current checkpointed lifecycle state."""

        return _state_from_snapshot(await self._graph.aget_state(self._config))

    async def is_waiting_for_human(self) -> bool:
        """Return whether this exact graph thread is currently interrupted."""

        return _is_interrupted(await self._graph.aget_state(self._config))


__all__ = (
    "PlannerGraphState",
    "PlannerRuntime",
    "PlannerRuntimeContext",
    "PlannerTurnOutcome",
)

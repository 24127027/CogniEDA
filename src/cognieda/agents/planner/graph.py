"""Planner-owned LangGraph topology and in-process checkpoint construction."""

from __future__ import annotations

import pickle
from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .dependencies import PlanAdmissionPort, PlannerContextProviderPort
from .nodes import admit_candidate, await_human, plan_or_answer
from .state import PlannerState
from .types import PlannerOutput


class InProcessPlannerSerializer(SerializerProtocol):
    """Round-trip trusted process-local typed state without weakening validation."""

    def dumps_typed(self, obj: Any) -> tuple[str, bytes]:
        return "pickle", pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def loads_typed(self, data: tuple[str, bytes]) -> Any:
        kind, payload = data
        if kind != "pickle":
            raise ValueError("In-process Planner checkpoint has an unknown payload type.")
        return pickle.loads(payload)


def build_graph(
    checkpointer: BaseCheckpointSaver[Any],
    *,
    invoke_cognitive: Callable[..., Awaitable[PlannerOutput]],
    planner_context_provider: PlannerContextProviderPort,
    plan_admission: PlanAdmissionPort,
) -> CompiledStateGraph[
    PlannerState,
    None,
    PlannerState,
    PlannerState,
]:
    """Compile the current Planner lifecycle without an execution node."""

    builder = StateGraph(PlannerState)
    builder.add_node(
        "plan_or_answer",
        partial(
            plan_or_answer,
            invoke_cognitive=invoke_cognitive,
            planner_context_provider=planner_context_provider,
        ),
        destinations=("await_human", "admit_candidate", END),
    )
    builder.add_node("await_human", await_human)
    builder.add_node(
        "admit_candidate",
        partial(admit_candidate, plan_admission=plan_admission),
    )

    builder.add_edge(START, "plan_or_answer")
    builder.add_edge("await_human", "plan_or_answer")
    builder.add_edge("admit_candidate", END)

    return builder.compile(checkpointer=checkpointer)


__all__ = (
    "InProcessPlannerSerializer",
    "build_graph",
)

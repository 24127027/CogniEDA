"""Planner-owned LangGraph topology and in-process checkpoint construction."""

from __future__ import annotations

import pickle
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .dependencies import PlannerGraphContext
from .nodes import admit_candidate, await_human, plan_or_answer
from .state import PlannerState


class InProcessPlannerSerializer(SerializerProtocol):
    """Round-trip trusted process-local typed state without weakening validation."""

    def dumps_typed(self, obj: Any) -> tuple[str, bytes]:
        return "pickle", pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)

    def loads_typed(self, data: tuple[str, bytes]) -> Any:
        kind, payload = data
        if kind != "pickle":
            raise ValueError("In-process Planner checkpoint has an unknown payload type.")
        return pickle.loads(payload)


def create_in_memory_checkpointer() -> BaseCheckpointSaver[Any]:
    """Create the current process-local Planner checkpoint boundary."""

    return InMemorySaver(serde=InProcessPlannerSerializer())


def build_graph(
    checkpointer: BaseCheckpointSaver[Any],
) -> CompiledStateGraph[
    PlannerState,
    PlannerGraphContext,
    PlannerState,
    PlannerState,
]:
    """Compile the current Planner lifecycle without an execution node."""

    builder = StateGraph(PlannerState, context_schema=PlannerGraphContext)
    builder.add_node("plan_or_answer", plan_or_answer)
    builder.add_node("await_human", await_human)
    builder.add_node("admit_candidate", admit_candidate)

    builder.add_edge(START, "plan_or_answer")
    builder.add_edge("admit_candidate", END)

    return builder.compile(checkpointer=checkpointer)


__all__ = (
    "InProcessPlannerSerializer",
    "build_graph",
    "create_in_memory_checkpointer",
)

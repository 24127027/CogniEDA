from collections.abc import Callable
from typing import Any

from langgraph.graph.state import CompiledStateGraph
from pydantic import TypeAdapter

from schemas.data_explorer_contracts import DataExplorerResult

from .capabilities import CapabilitySpec
from .types import BaseState, ExecutorContext, ExecutorInput


class Executor[StateT: BaseState]:
    """Role-neutral LangGraph scaffold with no durable-state ownership."""

    subcapabilities: list[CapabilitySpec]

    def __init__(
        self,
        graph_builder: Callable[
            ..., CompiledStateGraph[StateT, ExecutorContext, ExecutorInput, Any]
        ],
    ) -> None:
        if not callable(graph_builder):
            raise ValueError("graph_builder must be a callable that returns a CompiledStateGraph.")
        self.graph = graph_builder()

    async def run(self, input: ExecutorInput, context: ExecutorContext) -> Any:
        return await self.graph.ainvoke(
            input=input,
            context=context,
        )


class DataExplorerExecutor[StateT: BaseState](Executor[StateT]):
    """LangGraph adapter whose public output is the canonical Data Explorer result."""

    async def run(self, input: ExecutorInput, context: ExecutorContext) -> DataExplorerResult:
        result = await super().run(input=input, context=context)
        return TypeAdapter(DataExplorerResult).validate_python(result)

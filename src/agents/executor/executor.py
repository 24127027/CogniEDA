from collections.abc import Callable
from typing import Any

from langgraph.graph.state import CompiledStateGraph
from pydantic import TypeAdapter

from schemas.data_explorer_contracts import DataExplorerResult

from .capabilities import CapabilitySpec
from .types import BaseState, DataExplorerExecutionContext, DataExplorerInput


class DataExplorerAdapter[StateT: BaseState]:
    """LangGraph adapter whose public output is the canonical Data Explorer result."""

    subcapabilities: list[CapabilitySpec]

    def __init__(
        self,
        graph_builder: Callable[
            ..., CompiledStateGraph[StateT, DataExplorerExecutionContext, DataExplorerInput, Any]
        ],
    ) -> None:
        if not callable(graph_builder):
            raise ValueError("graph_builder must be a callable that returns a CompiledStateGraph.")
        self.graph = graph_builder()

    async def run(
        self, input: DataExplorerInput, context: DataExplorerExecutionContext
    ) -> DataExplorerResult:
        result = await self.graph.ainvoke(
            input=input,
            context=context,
        )
        return TypeAdapter(DataExplorerResult).validate_python(result)


DataExplorerExecutor = DataExplorerAdapter

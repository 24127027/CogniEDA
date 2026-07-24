from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from langgraph.graph.state import CompiledStateGraph
from pydantic import TypeAdapter

from schemas.data_explorer_contracts import DataExplorerResult

from .types import DataExplorerExecutionContext, DataExplorerInput


@runtime_checkable
class DataExplorerAdapterProtocol(Protocol):
    """The complete callable surface accepted by Data Explorer dispatch."""

    async def run(
        self,
        input: DataExplorerInput,
        context: DataExplorerExecutionContext,
    ) -> DataExplorerResult:
        ...


class DataExplorerAdapter:
    """LangGraph adapter whose public output is the canonical Data Explorer result."""

    def __init__(
        self,
        graph_builder: Callable[
            ..., CompiledStateGraph[Any, DataExplorerExecutionContext, DataExplorerInput, Any]
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

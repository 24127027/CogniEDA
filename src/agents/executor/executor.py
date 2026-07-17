from collections.abc import Callable

from langgraph.graph.state import CompiledStateGraph

from application.orchestrator.execution_contracts import ExecutorResult

from .capabilities import CapabilitySpec
from .types import BaseState, ExecutorContext, ExecutorInput


class Executor[StateT: BaseState]:
    """Stateless Executor"""

    subcapabilities: list[CapabilitySpec]

    def __init__(
        self,
        graph_builder: Callable[
            ..., CompiledStateGraph[StateT, ExecutorContext, ExecutorInput, ExecutorResult]
        ],
    ) -> None:
        if not callable(graph_builder):
            raise ValueError("graph_builder must be a callable that returns a CompiledStateGraph.")
        self.graph = graph_builder()

    # LangGraph's type hints declare `ainvoke()` as returning `dict[str, Any] | Any`.
    # The executor boundary validates the graph output into `ExecutorResult`.
    async def run(self, input: ExecutorInput, context: ExecutorContext) -> ExecutorResult:
        result = await self.graph.ainvoke(
            input=input,
            context=context,
        )

        return ExecutorResult.model_validate(result)

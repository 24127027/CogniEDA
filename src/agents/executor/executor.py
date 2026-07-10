from collections.abc import Callable

from langgraph.graph.state import CompiledStateGraph

from .types import BaseState, ExecutionResult, ExecutorContext, ExecutorInput
from .capabilities import CapabilitySpec, CAPABILITY_IDS
class Executor[StateT: BaseState]:
    """Stateless Executor"""
    subcapabilities: list[CapabilitySpec]

    def __init__(
        self,
        graph_builder: Callable[
            ..., CompiledStateGraph[StateT, ExecutorContext, ExecutorInput, ExecutionResult]
        ],
    ) -> None:
        if not callable(graph_builder):
            raise ValueError("graph_builder must be a callable that returns a CompiledStateGraph.")
        self.graph = graph_builder()

    # LangGraph's type hints declare `ainvoke()` as returning `dict[str, Any] | Any`.
    # The executor boundary validates the graph output into `ExecutionResult`.
    async def run(self, input: ExecutorInput, context: ExecutorContext) -> ExecutionResult:
        result = await self.graph.ainvoke(
            input=input,
            context=context,
        )

        return ExecutionResult.model_validate(result)

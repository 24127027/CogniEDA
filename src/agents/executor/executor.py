from __future__ import annotations

from collections.abc import Callable

from langgraph.graph.state import CompiledStateGraph

from .types import BaseState, ExecutionResult, ExecutorContext, ExecutorInput


class Executor[StateT: BaseState]:
    """Shared execution boundary for specialist executors."""

    def __init__(
        self,
        graph_builder: Callable[
            ...,
            CompiledStateGraph[
                StateT,
                ExecutorContext,
                ExecutorInput,
                ExecutionResult,
            ],
        ],
    ) -> None:
        if not callable(graph_builder):
            raise ValueError(
                "graph_builder must be a callable that returns a CompiledStateGraph."
            )

        self.graph = graph_builder()

    async def run(
        self,
        input: ExecutorInput,
        context: ExecutorContext,
    ) -> ExecutionResult:
        result = await self.graph.ainvoke(
            input=input,
            context=context,
        )

        return ExecutionResult.model_validate(result)
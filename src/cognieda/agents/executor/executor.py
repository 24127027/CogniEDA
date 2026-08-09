from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .types import BaseState, ExecutionRequest, ExecutionResult


class Executor[StateT: BaseState, ResultT: ExecutionResult]:
    """Graph-backed specialist base with a role-native validated result type."""

    def __init__(
        self,
        graph_builder: Callable[..., Any],
        *,
        result_type: type[ResultT],
    ) -> None:
        if not callable(graph_builder):
            raise ValueError("graph_builder must be callable.")

        self.graph: Any = graph_builder()
        self._result_type = result_type

    async def run(self, request: ExecutionRequest) -> ResultT:
        result = await self.graph.ainvoke(
            input=request.input,
            context=request.context,
        )
        return self._result_type.model_validate(result)

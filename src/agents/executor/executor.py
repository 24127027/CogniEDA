from langgraph.graph.state import CompiledStateGraph
from typing import Callable, Generic, TypeVar, cast
from abc import ABC, abstractmethod
from .types import Input, ExecutionResult, Context, BaseState

StateT = TypeVar('StateT', bound=BaseState)

class Executor(Generic[StateT], ABC):
    """Stateless Executor"""
    def __init__(self, graph_builder: Callable[..., CompiledStateGraph[StateT, Context, Input, StateT]]):
        if not callable(graph_builder):
            raise ValueError("graph_builder must be a callable that returns a CompiledStateGraph.")
        self.graph = graph_builder()
    
    # LangGraph's type hints declare `ainvoke()` as returning `dict[str, Any] | Any`.
    # In this framework, every executor graph is constructed to return `StateT`,
    # so we narrow the type for static type checking.
    async def run(self, input: Input, context: Context) -> ExecutionResult:
        state = cast(
            StateT,
            await self.graph.ainvoke(
                input=input,
                context=context,
            ),
        )

        return await self.prepare_output(state)
        
    @abstractmethod
    async def prepare_output(self, state: StateT) -> ExecutionResult:
        """Prepare the output from the final state."""

        
    
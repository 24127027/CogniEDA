from typing import Generic, TypeVar
from abc import ABC, abstractmethod

from langgraph.graph.state import CompiledStateGraph

from .types import AgentRequest, AgentResult

ReqT = TypeVar("ReqT", bound=AgentRequest)
ResT = TypeVar("ResT", bound=AgentResult)

class BaseAgent(ABC, Generic[ReqT, ResT]):
    def __init__(self, graph: CompiledStateGraph):
        self.graph = graph

    async def run(self, input: ReqT) -> ResT:
        """Run the agent with the given input and return the output."""
        
        await self.before_run(input)

        output = await self.graph.ainvoke(input)

        return await self.after_run(output)


    async def before_run(self, input: ReqT):
        """Hook to run before the main run method. Can be overridden by subclasses."""
        pass

    @abstractmethod
    async def after_run(self, output: dict) -> ResT:
        """
        Receives the final TypedDict state from LangGraph,
        extracts the final payload, and converts it to the expected ResT.
        """
        pass

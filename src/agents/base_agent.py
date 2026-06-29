from typing import Generic, TypeVar
from abc import ABC, abstractmethod

from langgraph.graph.state import CompiledStateGraph

from .types import AgentRequest, AgentResult, BaseState

ReqT = TypeVar("ReqT", bound=AgentRequest)
ResT = TypeVar("ResT", bound=AgentResult)
StateT = TypeVar("StateT", bound=BaseState)

class BaseAgent(ABC, Generic[ReqT, ResT, StateT]):
    def __init__(self, graph: CompiledStateGraph):
        self.graph = graph

    async def run(self, input: ReqT) -> ResT:
        """Run the agent with the given input and return the output."""
        
        preprocessed_input = await self.before_run(input)

        output = await self.graph.ainvoke(preprocessed_input)

        return await self.after_run(output) # type: ignore

    @abstractmethod
    async def before_run(self, input: ReqT) -> StateT:
        """
        Preprocesses the input and prepares the state for the graph invocation.
        This method can be overridden by subclasses to implement custom preprocessing logic.
        """        
        ...  

    @abstractmethod
    async def after_run(self, output: StateT) -> ResT:
        """
        Receives the final TypedDict state from LangGraph,
        extracts the final payload, and converts it to the expected ResT.
        """
        ...  

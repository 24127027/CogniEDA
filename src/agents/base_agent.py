"""Base class for graph-backed agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import cast

from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from agents.types import BaseState


class BaseAgent[ReqT: BaseModel, ResT: BaseModel, StateT: BaseState](ABC):
    """Small async wrapper around a compiled LangGraph graph."""

    def __init__(self, graph: CompiledStateGraph) -> None:
        self.graph = graph

    async def run(self, input: ReqT) -> ResT:
        """Run the agent with typed input and return typed output."""

        preprocessed_input = await self.before_run(input)
        output = await self.graph.ainvoke(preprocessed_input)
        return await self.after_run(cast(StateT, output))

    @abstractmethod
    async def before_run(self, input: ReqT) -> StateT:
        """Prepare graph state from agent-specific input."""

    @abstractmethod
    async def after_run(self, output: StateT) -> ResT:
        """Convert final graph state to agent-specific output."""

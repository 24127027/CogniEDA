"""Compatibility guard: Hypothesis Analyst is not a generic executor graph."""

from __future__ import annotations

from typing import Any

from langgraph.graph.state import CompiledStateGraph

from ..types import ExecutorContext, ExecutorInput
from .state import State


def build_graph() -> CompiledStateGraph[State, ExecutorContext, ExecutorInput, Any]:
    """Build the compiled state graph for HypothesisAnalyst."""
    raise NotImplementedError("HypothesisAnalyst uses its isolated PydanticAI evaluation boundary.")

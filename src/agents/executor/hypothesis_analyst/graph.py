"""Compatibility guard: Hypothesis Analyst is not a generic Data Explorer graph."""

from __future__ import annotations

from typing import Any


def build_graph() -> Any:
    """Build the compiled state graph for HypothesisAnalyst."""
    raise NotImplementedError("HypothesisAnalyst uses its isolated PydanticAI evaluation boundary.")

"""Hypothesis-analysis executor wrapper."""

from __future__ import annotations

from tools.builtin_tools import AvailableBuiltinTools

from ..capabilities import Capability
from ..executor import Executor
from ..registry import executor_registry
from .graph import build_graph
from .state import State


@executor_registry.register(Capability.HYPOTHESIS_TESTING)
class HypothesisAnalyst(Executor[State]):
    """Executor that can produce Evidence and Discovery drafts."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = (AvailableBuiltinTools.DATASET,)

    def __init__(self) -> None:
        super().__init__(build_graph)


HypothesisAnalystExecutor = HypothesisAnalyst

__all__ = ("HypothesisAnalyst", "HypothesisAnalystExecutor")

"""Hypothesis-analysis executor wrapper."""

from __future__ import annotations

from ..executor import Executor
from .state import State    
from .graph import build_graph


class HypothesisAnalyst(Executor[State]):
    """Executor that can produce Evidence and Discovery drafts."""

    def __init__(self) -> None:
        super().__init__(build_graph)
    

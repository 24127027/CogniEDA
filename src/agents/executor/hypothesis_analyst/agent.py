"""Hypothesis Analyst facade kept outside generic Data Explorer dispatch."""

from __future__ import annotations

from .nodes import build_hypothesis_analyst_agent


class HypothesisAnalyst:
    """No-tool factory facade for protected evidence evaluation."""

    builtin_tools: tuple[()] = ()
    build_agent = staticmethod(build_hypothesis_analyst_agent)


HypothesisAnalystExecutor = HypothesisAnalyst

__all__ = ("HypothesisAnalyst", "HypothesisAnalystExecutor")

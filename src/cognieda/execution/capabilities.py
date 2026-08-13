"""Execution-owned finite capability contract for provider dispatch."""

from enum import StrEnum


class Capability(StrEnum):
    """Finite requirements resolved through the executor registry."""

    DATA_ANALYSIS = "data_analysis"
    DATA_PROFILING = "data_profiling"
    DATA_TRANSFORMATION = "data_transformation"
    GRAPH_MINING = "graph_mining"
    HYPOTHESIS_TESTING = "hypothesis_testing"


__all__ = ("Capability",)

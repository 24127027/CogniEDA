"""Data Explorer agent package."""

from .agent import DataExplorer
from .contracts import (
    CorrelationMethod,
    DataAnalysisOperation,
    DataAnalysisPlan,
    DataAnalysisPlannerPort,
    DataAnalysisPlanningRequest,
    DataExplorerInput,
    DataExplorerObservation,
    DataExplorerResult,
    DataExecutionProvenance,
    DataProfileCandidate,
)
from .dependencies import DEDependencies
from .planning import DataAnalysisPlanner, UnsupportedAnalysisRequest

__all__ = (
    # Primary executor
    "DataExplorer",
    # Contract types
    "CorrelationMethod",
    "DataAnalysisOperation",
    "DataAnalysisPlan",
    "DataAnalysisPlannerPort",
    "DataAnalysisPlanningRequest",
    "DataExplorerInput",
    "DataExplorerObservation",
    "DataExplorerResult",
    "DataExecutionProvenance",
    "DataProfileCandidate",
    # Dependencies (used by LangGraph nodes)
    "DEDependencies",
    # Planning
    "DataAnalysisPlanner",
    "UnsupportedAnalysisRequest",
)

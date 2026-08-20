from typing import Any, TypedDict
from cognieda.schemas.artifacts import DataProfile, Evidence

class State(TypedDict, total=False):
    """Represents the internal state of the DataExplorer agent."""
    input: str
    external_context: str
    artifacts: list[DataProfile | Evidence]
    messages: list[Any]
    feedback: str
    iterations: int
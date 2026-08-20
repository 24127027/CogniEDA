from typing import Any, TypedDict
from cognieda.schemas.artifacts import DataProfile, Evidence

class State(TypedDict, total=False):
    input: str
    artifacts: list[DataProfile | Evidence]
    messages: list[Any]
    feedback: str
    iterations: int
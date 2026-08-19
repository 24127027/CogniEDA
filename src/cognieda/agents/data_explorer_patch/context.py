from pydantic_ai import Agent
from dataclasses import dataclass
from .dependencies import DataExplorerDeps
@dataclass
class Context:
    agent: Agent[DataExplorerDeps]
    deps: DataExplorerDeps
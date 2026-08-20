from pydantic_ai import Agent
from dataclasses import dataclass
from .dependencies import DataExplorerDeps
from cognieda.delegation.contracts import ExecutorContext
@dataclass
class Context:
    agent: Agent[DataExplorerDeps]
    deps: DataExplorerDeps
    context: ExecutorContext